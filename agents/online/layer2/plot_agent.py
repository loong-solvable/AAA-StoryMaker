"""
命运编织者 (Plot Director)
游戏的导演和编剧，负责剧情走向和场景设计
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
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
        self.plot_hints = genesis_data.get("plot_hints", [])
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
        logger.info(f"   - 剧情线索总数: {len(self.plot_hints)}")
    
    def _load_system_prompt(self) -> str:
        """加载系统提示词并填充变量、转义花括号"""
        prompt_file = settings.PROMPTS_DIR / "online" / "plot_system.txt"
        
        with open(prompt_file, "r", encoding="utf-8") as f:
            template = f.read()
        
        # 填充初始化时可用的变量
        if "{characters_list}" in template:
            characters_list = [
                {"id": char.get("id"), "name": char.get("name"), "importance": char.get("importance", 0.2)}
                for char in self.characters
            ]
            template = template.replace(
                "{characters_list}", json.dumps(characters_list, ensure_ascii=False, indent=2)
            )
        
        if "{world_setting}" in template:
            world_setting_summary = {
                "world_name": self.world_info.get("title", "未知世界"),
                "genre": self.world_info.get("genre", "未知类型"),
                "locations": self.genesis_data.get("locations", [])
            }
            template = template.replace(
                "{world_setting}", json.dumps(world_setting_summary, ensure_ascii=False, indent=2)
            )
        
        # 提取玩家名字（从characters中找is_player=True或id=user的角色）
        player_name = "玩家"  # 默认值
        for char in self.characters:
            if char.get("is_player") or char.get("id") == "user":
                player_name = char.get("name", "玩家")
                break

        # 替换玩家名字占位符
        if "{player_name}" in template:
            template = template.replace("{player_name}", player_name)

        # 填充运行时变量（使用占位符，因为这些数据在 plot_agent.py 中无法获取）
        for var, placeholder in [
            ("{world_state}", "（世界状态将在运行时提供）"),
            ("{story_history}", "（暂无历史剧情摘要）"),
            ("{last_scene_dialogues}", "（暂无上一幕对话）"),
            ("{characters_details}", "（角色详情已在 characters_list 中）"),
            ("{user_action}", "（玩家行动将在运行时提供）")
        ]:
            if var in template:
                template = template.replace(var, placeholder)
        
        # 转义所有剩余的花括号，避免 LangChain 解析错误
        template = template.replace("{", "{{").replace("}", "}}")
        
        return template
    
    def _build_chain(self):
        """构建处理链"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", """请为当前场景生成剧本指令：

【世界背景】
世界：{world_name}
类型：{genre}

【当前幕目标】
幕名称：{act_name}
幕目标：{act_objective}
当前进度：{act_progress}
推进紧迫度：{act_urgency}（0=不急，1=非常紧迫）
剩余回合：{turns_remaining}
导演提示：{act_guidance}

【剧情节点信息】
可用剧情节点：
{available_plots}

已完成节点：{completed_nodes}
当前激活节点：{active_nodes}

【历史剧情摘要】
{story_history}

【上一幕发生的事】
{last_scene_dialogues}

【当前情况】
场景编号：第{scene_number}幕
玩家行动：{player_action}
玩家位置：{player_location}
在场角色：{present_characters}

【世界状态摘要】
{world_context}

【待融入的事件】
{triggered_events}

请按照系统提示词中的格式要求生成场景剧本。
注意：根据幕目标和紧迫度调整剧情推进节奏。紧迫度越高，越应主动推进剧情；紧迫度低时可让玩家自由探索。""")
        ])

        return prompt | self.llm | StrOutputParser()
    
    def generate_scene_script(
        self,
        player_action: str,
        player_location: str,
        present_characters: List[str],
        world_context: Dict[str, Any],
        story_history: str = "",
        last_scene_dialogues: str = "",
        act_context: Optional[Dict[str, Any]] = None,
        triggered_events: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        生成场景剧本

        Args:
            player_action: 玩家行动
            player_location: 玩家位置
            present_characters: 在场角色ID列表
            world_context: 世界状态上下文
            story_history: 历史剧情摘要（来自MemoryManager）
            last_scene_dialogues: 上一幕的对话记录
            act_context: 幕目标上下文（来自ActDirector）
            triggered_events: 触发的事件列表（来自EventEngine）

        Returns:
            场景剧本数据
        """
        logger.info(f"🎬 生成第 {self.scene_count + 1} 幕剧本...")

        self.scene_count += 1

        # 构建剧情节点描述
        available_plots = self._format_available_plots()

        # 构建角色名称列表（包含importance权重信息）
        char_names = []
        char_importance_info = []
        for char_id in present_characters:
            char_data = next((c for c in self.characters if c.get("id") == char_id), None)
            if char_data:
                char_name = char_data.get("name", char_id)
                importance = char_data.get("importance", 50.0)
                char_names.append(char_name)
                char_importance_info.append(f"{char_name}(权重:{importance})")

        logger.info(f"   - 在场角色权重: {', '.join(char_importance_info)}")

        # 处理幕目标上下文
        if act_context:
            act_name = act_context.get("act_name", "自由探索")
            act_objective = act_context.get("objective", "")
            act_progress = f"{act_context.get('progress', 0) * 100:.0f}%"
            act_urgency = f"{act_context.get('urgency', 0.5):.1f}"
            turns_remaining = act_context.get("turns_remaining", 999)
            act_guidance = act_context.get("guidance", "")
            logger.info(f"   - 幕目标: {act_name}, 紧迫度: {act_urgency}")
        else:
            act_name = "自由探索"
            act_objective = "响应玩家的探索行为"
            act_progress = "N/A"
            act_urgency = "0.5"
            turns_remaining = 999
            act_guidance = ""

        # 处理触发事件
        if triggered_events:
            events_desc = "\n".join([
                f"- {e.get('event_name', '未知事件')}: {e.get('description', '')}"
                for e in triggered_events
            ])
            logger.info(f"   - 触发事件: {len(triggered_events)} 个")
        else:
            events_desc = "（无待融入事件）"

        try:
            response = self.chain.invoke({
                "world_name": self.world_info.get("title", "未知世界"),
                "genre": self.world_info.get("genre", "未知类型"),
                "act_name": act_name,
                "act_objective": act_objective,
                "act_progress": act_progress,
                "act_urgency": act_urgency,
                "turns_remaining": turns_remaining,
                "act_guidance": act_guidance if act_guidance else "（无特定引导）",
                "available_plots": available_plots,
                "completed_nodes": ", ".join(self.completed_nodes) if self.completed_nodes else "无",
                "active_nodes": ", ".join(self.active_nodes) if self.active_nodes else "无",
                "story_history": story_history if story_history else "（这是故事的开始）",
                "last_scene_dialogues": last_scene_dialogues if last_scene_dialogues else "（这是第一幕）",
                "scene_number": self.scene_count,
                "player_action": player_action,
                "player_location": player_location,
                "present_characters": ", ".join(char_names) if char_names else "无",
                "world_context": json.dumps(world_context, ensure_ascii=False, indent=2),
                "triggered_events": events_desc
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

    async def async_generate_scene_script(
        self,
        player_action: str,
        player_location: str,
        present_characters: List[str],
        world_context: Dict[str, Any],
        story_history: str = "",
        last_scene_dialogues: str = "",
        act_context: Optional[Dict[str, Any]] = None,
        triggered_events: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        异步版本的剧本生成，使用线程池执行
        """
        return await asyncio.to_thread(
            self.generate_scene_script,
            player_action,
            player_location,
            present_characters,
            world_context,
            story_history,
            last_scene_dialogues,
            act_context,
            triggered_events
        )

    def _format_available_plots(self) -> str:
        """格式化可用的剧情线索"""
        lines = []
        for i, hint in enumerate(self.plot_hints[:10], 1):  # 只显示前10个
            if hint.get("id") not in self.completed_nodes:
                lines.append(
                    f"{i}. [{hint.get('id')}] {hint.get('title', '未知')}"
                    f" - 重要性: {hint.get('importance', 'minor')}"
                )
        return "\n".join(lines) if lines else "无可用剧情节点"
    
    def _parse_script(self, response: str) -> Dict[str, Any]:
        """
        解析剧本（支持 JSON 和文本格式）
        
        plot_system.txt 要求输出文本格式（使用【】作为板块标题），
        因此需要解析文本格式的剧本。
        """
        response = response.strip()
        
        # 尝试解析 JSON 格式
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        # 如果是 JSON 格式，直接解析
        if response.startswith("{"):
            try:
                data = json.loads(response)
                return data
            except json.JSONDecodeError:
                pass  # 继续尝试文本格式解析
        
        # 解析文本格式（【剧情】【世界与物理事件】【角色登场与调度】）
        return self._parse_text_script(response)
    
    def _parse_text_script(self, response: str) -> Dict[str, Any]:
        """
        解析文本格式的剧本
        
        文本格式示例：
        【剧情】
        - **剧情推演**: ...
        
        【世界与物理事件】
        - **时间流逝**: ...
        - **环境变动**: ...
        - **位置变动**: ...
        
        【角色登场与调度】
        - **入场**: 角色名 (ID) [First Appearance: True/False] - *描述*
        - **离场**: 角色名 (ID) - *原因*
        - **在场**: 角色名 (ID) - *状态*
        
        【幕进度评估】
        - **幕完成信号**: CONTINUE / READY_TO_END / FORCE_END
        - **结束理由**: ...
        - **下一幕建议**: ...
        """
        import re
        
        result = {
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
            "director_notes": "",
            "act_completion": {
                "signal": "CONTINUE",
                "reason": "",
                "next_act_suggestion": ""
            },
            "raw_content": response  # 保存原始文本
        }
        
        # 提取【剧情】部分
        plot_match = re.search(r'【剧情】(.*?)(?=【|$)', response, re.DOTALL)
        if plot_match:
            plot_content = plot_match.group(1).strip()
            result["director_notes"] = plot_content
            
            # 从剧情内容推断情绪
            if any(word in plot_content for word in ["紧张", "危险", "冲突", "争吵"]):
                result["scene_theme"]["mood"] = "紧张"
            elif any(word in plot_content for word in ["温馨", "友好", "轻松", "愉快"]):
                result["scene_theme"]["mood"] = "温馨"
            elif any(word in plot_content for word in ["悲伤", "难过", "失落"]):
                result["scene_theme"]["mood"] = "忧郁"
        
        # 提取【角色登场与调度】部分
        cast_match = re.search(r'【角色登场与调度】(.*?)(?=【|$)', response, re.DOTALL)
        if cast_match:
            cast_content = cast_match.group(1).strip()
            
            # 解析入场角色
            entry_matches = re.findall(r'\*\*入场\*\*:\s*(\S+)\s*\((\w+)\)\s*\[First Appearance:\s*(True|False)\]', cast_content)
            for name, char_id, first_appearance in entry_matches:
                result["instructions"].append({
                    "type": "character_entry",
                    "character_id": char_id,
                    "character_name": name,
                    "first_appearance": first_appearance.lower() == "true"
                })
            
            # 解析离场角色
            exit_matches = re.findall(r'\*\*离场\*\*:\s*(\S+)\s*\((\w+)\)', cast_content)
            for name, char_id in exit_matches:
                result["instructions"].append({
                    "type": "character_exit",
                    "character_id": char_id,
                    "character_name": name
                })
        
        # 提取【世界与物理事件】部分
        world_match = re.search(r'【世界与物理事件】(.*?)(?=【|$)', response, re.DOTALL)
        if world_match:
            world_content = world_match.group(1).strip()
            
            # 解析时间流逝
            time_match = re.search(r'\*\*时间流逝\*\*:\s*(.+?)(?=\n|$)', world_content)
            if time_match:
                result["time_passed"] = time_match.group(1).strip()
            
            # 解析位置变动
            location_match = re.search(r'\*\*位置变动\*\*:\s*(.+?)(?=\n|$)', world_content)
            if location_match:
                result["location_change"] = location_match.group(1).strip()
        
        # 提取【幕进度评估】部分
        act_match = re.search(r'【幕进度评估】(.*?)(?=【|$)', response, re.DOTALL)
        if act_match:
            act_content = act_match.group(1).strip()
            
            # 解析幕完成信号
            signal_match = re.search(r'\*\*幕完成信号\*\*:\s*(CONTINUE|READY_TO_END|FORCE_END)', act_content, re.IGNORECASE)
            if signal_match:
                result["act_completion"]["signal"] = signal_match.group(1).upper()
            
            # 解析结束理由
            reason_match = re.search(r'\*\*结束理由\*\*:\s*(.+?)(?=\n|$)', act_content)
            if reason_match:
                result["act_completion"]["reason"] = reason_match.group(1).strip()
            
            # 解析下一幕建议
            next_act_match = re.search(r'\*\*下一幕建议\*\*:\s*(.+?)(?=\n|$)', act_content)
            if next_act_match:
                result["act_completion"]["next_act_suggestion"] = next_act_match.group(1).strip()
        
        logger.info(f"📝 解析文本格式剧本: {len(result['instructions'])} 条指令, 幕信号: {result['act_completion']['signal']}")
        return result
    
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
    
    def get_high_importance_characters(self, min_importance: float = 70.0) -> List[Dict[str, Any]]:
        """
        获取高权重角色（用于重要剧情场景）
        
        Args:
            min_importance: 最低权重阈值（0-100）
        
        Returns:
            高权重角色列表
        """
        high_importance_chars = []
        for char in self.characters:
            importance = char.get("importance", 50.0)
            if importance >= min_importance:
                high_importance_chars.append({
                    "id": char.get("id"),
                    "name": char.get("name"),
                    "importance": importance
                })
        
        # 按权重排序
        high_importance_chars.sort(key=lambda x: x["importance"], reverse=True)
        return high_importance_chars
    
    def suggest_scene_characters(self, location: str, scene_importance: str = "normal") -> List[str]:
        """
        根据场景重要性和角色权重，建议应该出现的角色
        
        Args:
            location: 场景位置
            scene_importance: 场景重要性（"high", "normal", "low"）
        
        Returns:
            建议出现的角色ID列表
        """
        # 根据场景重要性设置权重阈值
        importance_thresholds = {
            "high": 80.0,    # 高潮场景：只让权重80+的角色出现
            "normal": 50.0,  # 常规场景：权重50+的角色
            "low": 0.0       # 过渡场景：任何角色都可能出现
        }
        
        threshold = importance_thresholds.get(scene_importance, 50.0)
        
        suggested = []
        for char in self.characters:
            importance = char.get("importance", 50.0)
            char_id = char.get("id")
            
            # 基于权重和阈值决定
            if importance >= threshold:
                suggested.append(char_id)
        
        logger.info(f"📋 场景角色建议（{scene_importance}）: {len(suggested)}个角色（权重≥{threshold}）")
        return suggested
    
    def get_plot_status(self) -> Dict[str, Any]:
        """获取剧情状态"""
        return {
            "current_stage": self.current_stage,
            "scene_count": self.scene_count,
            "completed_nodes": self.completed_nodes,
            "active_nodes": self.active_nodes,
            "total_hints": len(self.plot_hints),
            "completion_rate": len(self.completed_nodes) / len(self.plot_hints) if self.plot_hints else 0
        }

    def get_state_snapshot(self) -> Dict[str, Any]:
        """用于持久化的剧情状态快照"""
        status = dict(self.get_plot_status())
        status.update(
            {
                "available_hint_ids": [hint.get("id") for hint in self.plot_hints],
                "recent_completed": self.completed_nodes[-5:] if self.completed_nodes else [],
            }
        )
        return status
    
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

