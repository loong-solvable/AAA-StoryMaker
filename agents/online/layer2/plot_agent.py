"""
命运编织者 (Plot Director)
游戏的导演和编剧，负责剧情走向和场景设计
"""
import json
from typing import Dict, Any, List, Optional
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from utils.llm_factory import get_llm
from utils.logger import setup_logger
from config.settings import settings
from agents.message_protocol import Message, AgentRole, MessageType, PlotInstruction

logger = setup_logger("Plot", "plot.log")


class PlotDirector:
    """
    命运编织者Agent
    掌控剧情走向和节奏
    """
    
    def __init__(self, genesis_data: Dict[str, Any]):
        """
        初始化命运编织者
        
        Args:
            genesis_data: Genesis世界数据
        """
        logger.info("🎬 初始化命运编织者...")
        
        # LLM实例（较高温度以增加创造性）
        self.llm = get_llm(temperature=0.8)
        
        # Genesis数据
        self.genesis_data = genesis_data
        self.world_info = genesis_data.get("world", {})
        self.plot_nodes = genesis_data.get("plot_nodes", [])
        self.characters = genesis_data.get("characters", [])
        
        # 加载提示词
        self.system_prompt = self._load_system_prompt()
        
        # 构建链
        self.chain = self._build_chain()
        
        # 剧情状态
        self.completed_nodes: List[str] = []
        self.active_nodes: List[str] = []
        self.current_stage = "开端"
        self.scene_count = 0
        
        logger.info("✅ 命运编织者初始化完成")
        logger.info(f"   - 剧情节点总数: {len(self.plot_nodes)}")
    
    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        prompt_file = settings.PROMPTS_DIR / "online" / "plot_system.txt"
        
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()
    
    def _build_chain(self):
        """构建处理链"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", """请为当前场景生成剧本指令：

【世界背景】
世界：{world_name}
类型：{genre}

【剧情节点信息】
可用剧情节点：
{available_plots}

已完成节点：{completed_nodes}
当前激活节点：{active_nodes}

【当前情况】
场景编号：第{scene_number}幕
玩家行动：{player_action}
玩家位置：{player_location}
在场角色：{present_characters}

【世界状态摘要】
{world_context}

请生成场景剧本指令，返回JSON格式。""")
        ])
        
        return prompt | self.llm | StrOutputParser()
    
    def generate_scene_script(
        self,
        player_action: str,
        player_location: str,
        present_characters: List[str],
        world_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成场景剧本
        
        Args:
            player_action: 玩家行动
            player_location: 玩家位置
            present_characters: 在场角色ID列表
            world_context: 世界状态上下文
        
        Returns:
            场景剧本数据
        """
        logger.info(f"🎬 生成第 {self.scene_count + 1} 幕剧本...")
        
        self.scene_count += 1
        
        # 构建剧情节点描述
        available_plots = self._format_available_plots()
        
        # 构建角色名称列表
        char_names = []
        for char_id in present_characters:
            char_data = next((c for c in self.characters if c.get("id") == char_id), None)
            if char_data:
                char_names.append(char_data.get("name", char_id))
        
        try:
            response = self.chain.invoke({
                "world_name": self.world_info.get("title", "未知世界"),
                "genre": self.world_info.get("genre", "未知类型"),
                "available_plots": available_plots,
                "completed_nodes": ", ".join(self.completed_nodes) if self.completed_nodes else "无",
                "active_nodes": ", ".join(self.active_nodes) if self.active_nodes else "无",
                "scene_number": self.scene_count,
                "player_action": player_action,
                "player_location": player_location,
                "present_characters": ", ".join(char_names) if char_names else "无",
                "world_context": json.dumps(world_context, ensure_ascii=False, indent=2)
            })
            
            # 解析剧本
            script = self._parse_script(response)
            
            # 更新剧情状态
            self._update_plot_state(script)
            
            logger.info(f"✅ 剧本生成完成")
            logger.info(f"   - 场景主题: {script.get('scene_theme', {}).get('mood', '未知')}")
            logger.info(f"   - 指令数量: {len(script.get('instructions', []))}")
            
            return script
            
        except Exception as e:
            logger.error(f"❌ 剧本生成失败: {e}", exc_info=True)
            return self._create_minimal_script()
    
    def _format_available_plots(self) -> str:
        """格式化可用的剧情节点"""
        lines = []
        for i, node in enumerate(self.plot_nodes[:10], 1):  # 只显示前10个
            if node.get("id") not in self.completed_nodes:
                lines.append(
                    f"{i}. [{node.get('id')}] {node.get('title', '未知')}"
                    f" - 重要性: {node.get('importance', 'minor')}"
                )
        return "\n".join(lines) if lines else "无可用剧情节点"
    
    def _parse_script(self, response: str) -> Dict[str, Any]:
        """解析剧本"""
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            data = json.loads(response)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"❌ 解析剧本失败: {e}")
            logger.error(f"原始响应: {response[:200]}...")
            return self._create_minimal_script()
    
    def _update_plot_state(self, script: Dict[str, Any]):
        """更新剧情状态"""
        progression = script.get("plot_progression", {})
        
        # 更新已完成节点
        for node_id in progression.get("completed_nodes", []):
            if node_id not in self.completed_nodes:
                self.completed_nodes.append(node_id)
                logger.info(f"✅ 剧情节点完成: {node_id}")
        
        # 更新激活节点
        self.active_nodes = progression.get("activated_nodes", [])
        
        # 更新阶段
        stage = script.get("scene_analysis", {}).get("current_stage")
        if stage and stage != self.current_stage:
            logger.info(f"🎭 剧情进入新阶段: {self.current_stage} → {stage}")
            self.current_stage = stage
    
    def _create_minimal_script(self) -> Dict[str, Any]:
        """创建最小剧本（出错时使用）"""
        return {
            "scene_analysis": {
                "current_stage": self.current_stage,
                "tension_level": 5,
                "plot_significance": "常规场景",
                "narrative_goal": "推进剧情"
            },
            "scene_theme": {
                "mood": "平静",
                "tone": "日常",
                "pacing": "稳定"
            },
            "instructions": [],
            "plot_progression": {
                "completed_nodes": self.completed_nodes,
                "activated_nodes": self.active_nodes,
                "next_suggested_nodes": [],
                "branching_opportunities": []
            },
            "director_notes": "自动生成的最小剧本"
        }
    
    def get_plot_status(self) -> Dict[str, Any]:
        """获取剧情状态"""
        return {
            "current_stage": self.current_stage,
            "scene_count": self.scene_count,
            "completed_nodes": self.completed_nodes,
            "active_nodes": self.active_nodes,
            "total_nodes": len(self.plot_nodes),
            "completion_rate": len(self.completed_nodes) / len(self.plot_nodes) if self.plot_nodes else 0
        }
    
    def handle_message(self, message: Message) -> Optional[Message]:
        """处理消息（OS接口）"""
        if message.message_type == MessageType.DECISION_REQUEST:
            # 生成剧本决策
            payload = message.payload
            
            script = self.generate_scene_script(
                player_action=payload.get("player_action", ""),
                player_location=payload.get("player_location", ""),
                present_characters=payload.get("present_characters", []),
                world_context=payload.get("world_context", {})
            )
            
            from agents.message_protocol import create_message
            return create_message(
                from_agent=AgentRole.PLOT,
                to_agent=message.from_agent,
                message_type=MessageType.DECISION_RESPONSE,
                payload=script
            )
        
        return None

