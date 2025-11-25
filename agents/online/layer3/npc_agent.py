"""
NPC Agent - 演员组
动态生成的NPC角色，沉浸式扮演
使用新的JSON角色卡格式：traits, behavior_rules, relationship_matrix, voice_samples等
"""
import json
from typing import Dict, Any, Optional, List
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from utils.llm_factory import get_llm
from utils.logger import setup_logger
from config.settings import settings
from agents.message_protocol import Message, AgentRole, MessageType, GeneratedContent

logger = setup_logger("NPC", "npc.log")


class NPCAgent:
    """
    NPC Agent基类
    每个NPC都是一个独立的Agent实例
    """
    
    def __init__(self, character_data: Dict[str, Any]):
        """
        初始化NPC Agent
        
        Args:
            character_data: 角色数据（从Genesis提取，使用新的JSON角色卡格式）
        """
        self.character_id = character_data.get("id")
        self.character_name = character_data.get("name")
        
        logger.info(f"🎭 初始化NPC: {self.character_name} ({self.character_id})")
        
        # LLM实例
        self.llm = get_llm(temperature=0.8)
        
        # ==========================================
        # 1. 基础元数据 (Meta Info)
        # ==========================================
        self.character_data = character_data
        self.age = character_data.get("age", "未知")
        self.gender = character_data.get("gender", "未知")
        self.importance = character_data.get("importance", 50.0)  # 剧情权重 0-100
        
        # ==========================================
        # 2. 核心特质与逻辑 (Core Identity)
        # ==========================================
        self.traits = character_data.get("traits", [])  # 身份/性格/状态标签
        self.behavior_rules = character_data.get("behavior_rules", [])  # 行为逻辑准则
        
        # ==========================================
        # 3. 社交矩阵 (Relationship Matrix)
        # ==========================================
        self.relationship_matrix = character_data.get("relationship_matrix", {})  # 该角色"眼中的别人"
        
        # ==========================================
        # 4. 资产与外观 (Assets & Visuals)
        # ==========================================
        self.possessions = character_data.get("possessions", [])  # 关键持有物
        self.current_appearance = character_data.get("current_appearance", "")  # 外观描述（供Vibe使用）
        
        # ==========================================
        # 5. 语言样本 (Mimesis Data)
        # ==========================================
        self.voice_samples = character_data.get("voice_samples", [])  # 原文台词样本
        
        # 当前动态状态
        self.current_mood = "平静"
        self.current_location = ""
        self.current_activity = character_data.get("initial_state", "日常活动")
        
        # 加载提示词模板
        self.system_prompt_template = self._load_system_prompt()
        
        # 构建链
        self.chain = self._build_chain()
        
        # 对话历史
        self.dialogue_history: List[str] = []
        
        logger.info(f"✅ NPC {self.character_name} 初始化完成")
    
    def _load_system_prompt(self) -> str:
        """加载系统提示词模板"""
        prompt_file = settings.PROMPTS_DIR / "online" / "npc_system.txt"
        
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()
    
    def _build_chain(self):
        """构建处理链"""
        # 动态生成角色的系统提示（使用新的JSON字段）
        traits_str = ", ".join(self.traits) if self.traits else "普通人"
        behavior_rules_str = "\n".join([f"- {rule}" for rule in self.behavior_rules]) if self.behavior_rules else "无特殊行为准则"
        
        # 格式化社交矩阵
        relationship_lines = []
        for target_id, rel_data in self.relationship_matrix.items():
            address = rel_data.get("address_as", target_id)
            attitude = rel_data.get("attitude", "普通")
            relationship_lines.append(f"- {target_id}: 称呼为'{address}', 态度: {attitude}")
        relationships_str = "\n".join(relationship_lines) if relationship_lines else "暂无特殊关系"
        
        # 格式化语言样本（作为few-shot示例）
        voice_samples_str = "\n".join([f'"{sample}"' for sample in self.voice_samples[:3]]) if self.voice_samples else "无语言样本"
        
        system_prompt = self.system_prompt_template.format(
            character_name=self.character_name,
            age=self.age,
            gender=self.gender,
            traits=traits_str,
            behavior_rules=behavior_rules_str,
            relationships=relationships_str,
            voice_samples=voice_samples_str,
            current_mood="{current_mood}",
            current_location="{current_location}",
            current_activity="{current_activity}"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", """【当前场景】
{scene_context}

【导演指令】
{director_instruction}

【对话历史】
{dialogue_history}

【当前输入】
对方说："{player_input}"

请根据你的性格和当前情况做出反应，返回JSON格式。""")
        ])
        
        return prompt | self.llm | StrOutputParser()
    
    def react(
        self,
        player_input: str,
        scene_context: Dict[str, Any],
        director_instruction: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        对玩家输入做出反应
        
        Args:
            player_input: 玩家的输入/对话
            scene_context: 场景上下文
            director_instruction: 导演指令（可选）
        
        Returns:
            NPC的反应
        """
        logger.info(f"🎭 {self.character_name} 正在反应...")
        
        # 更新当前状态
        self.current_mood = director_instruction.get("parameters", {}).get("emotion", self.current_mood) if director_instruction else self.current_mood
        
        # 格式化导演指令
        director_str = self._format_director_instruction(director_instruction)
        
        # 格式化对话历史
        history_str = self._format_dialogue_history()
        
        try:
            # 动态填充当前状态（使用新的JSON字段）
            traits_str = ", ".join(self.traits) if self.traits else "普通人"
            behavior_rules_str = "\n".join([f"- {rule}" for rule in self.behavior_rules]) if self.behavior_rules else "无特殊行为准则"
            
            # 格式化社交矩阵
            relationship_lines = []
            for target_id, rel_data in self.relationship_matrix.items():
                address = rel_data.get("address_as", target_id)
                attitude = rel_data.get("attitude", "普通")
                relationship_lines.append(f"- {target_id}: 称呼为'{address}', 态度: {attitude}")
            relationships_str = "\n".join(relationship_lines) if relationship_lines else "暂无特殊关系"
            
            # 格式化语言样本
            voice_samples_str = "\n".join([f'"{sample}"' for sample in self.voice_samples[:3]]) if self.voice_samples else "无语言样本"
            
            prompt_with_state = self.system_prompt_template.format(
                character_name=self.character_name,
                age=self.age,
                gender=self.gender,
                traits=traits_str,
                behavior_rules=behavior_rules_str,
                relationships=relationships_str,
                voice_samples=voice_samples_str,
                current_mood=self.current_mood,
                current_location=self.current_location,
                current_activity=self.current_activity
            )
            
            # 重新构建链（包含当前状态）
            prompt = ChatPromptTemplate.from_messages([
                ("system", prompt_with_state),
                ("human", """【当前场景】
{scene_context}

【导演指令】
{director_instruction}

【对话历史】
{dialogue_history}

【当前输入】
对方说："{player_input}"

请根据你的性格和当前情况做出反应，返回JSON格式。""")
            ])
            
            chain = prompt | self.llm | StrOutputParser()
            
            response = chain.invoke({
                "scene_context": json.dumps(scene_context, ensure_ascii=False),
                "director_instruction": director_str,
                "dialogue_history": history_str,
                "player_input": player_input
            })
            
            # 解析反应
            reaction = self._parse_reaction(response)
            
            # 记录对话历史
            if reaction.get("dialogue"):
                self.dialogue_history.append(f"玩家: {player_input}")
                self.dialogue_history.append(f"{self.character_name}: {reaction['dialogue']}")
                if len(self.dialogue_history) > 10:  # 只保留最近5轮
                    self.dialogue_history = self.dialogue_history[-10:]
            
            # 更新情绪
            if reaction.get("emotion"):
                self.current_mood = reaction["emotion"]
            
            logger.info(f"✅ {self.character_name} 反应完成")
            logger.info(f"   - 情绪: {reaction.get('emotion', '未知')}")
            logger.info(f"   - 态度: {reaction.get('attitude', '未知')}")
            
            return reaction
            
        except Exception as e:
            logger.error(f"❌ {self.character_name} 反应生成失败: {e}", exc_info=True)
            return self._create_minimal_reaction()
    
    def _format_director_instruction(self, instruction: Optional[Dict[str, Any]]) -> str:
        """格式化导演指令"""
        if not instruction:
            return "无特殊指令，自然反应即可"
        
        params = instruction.get("parameters", {})
        lines = []
        
        if "emotion" in params:
            lines.append(f"- 情绪倾向：{params['emotion']}")
        if "attitude" in params:
            lines.append(f"- 对话态度：{params['attitude']}")
        if "reveal_info" in params:
            lines.append(f"- 信息揭露：{params['reveal_info']}")
        if "dialogue_style" in params:
            lines.append(f"- 对话风格：{params['dialogue_style']}")
        
        return "\n".join(lines) if lines else "自然反应"
    
    def _format_dialogue_history(self) -> str:
        """格式化对话历史"""
        if not self.dialogue_history:
            return "这是第一次对话"
        
        return "\n".join(self.dialogue_history[-6:])  # 最近3轮
    
    def _parse_reaction(self, response: str) -> Dict[str, Any]:
        """解析NPC反应"""
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
            logger.error(f"❌ 解析NPC反应失败: {e}")
            logger.error(f"原始响应: {response[:200]}...")
            return self._create_minimal_reaction()
    
    def _create_minimal_reaction(self) -> Dict[str, Any]:
        """创建最小反应（出错时使用）"""
        return {
            "thought": "...",
            "emotion": self.current_mood,
            "dialogue": "嗯...是的。",
            "action": "点了点头",
            "attitude": "平和"
        }
    
    def update_state(self, location: str = None, activity: str = None, mood: str = None):
        """更新NPC状态"""
        if location:
            self.current_location = location
        if activity:
            self.current_activity = activity
        if mood:
            self.current_mood = mood
    
    def get_state(self) -> Dict[str, Any]:
        """获取NPC当前状态"""
        return {
            "id": self.character_id,
            "name": self.character_name,
            "location": self.current_location,
            "activity": self.current_activity,
            "mood": self.current_mood
        }


class NPCManager:
    """
    NPC管理器
    负责动态创建和管理所有NPC
    """
    
    def __init__(self, genesis_data: Dict[str, Any]):
        """
        初始化NPC管理器
        
        Args:
            genesis_data: Genesis世界数据
        """
        logger.info("🎭 初始化NPC管理器...")
        
        self.genesis_data = genesis_data
        self.characters_data = genesis_data.get("characters", [])
        
        # NPC实例字典
        self.npcs: Dict[str, NPCAgent] = {}
        
        # 批量创建NPC
        self._create_all_npcs()
        
        logger.info(f"✅ NPC管理器初始化完成，创建了 {len(self.npcs)} 个NPC")
    
    def _create_all_npcs(self):
        """创建所有NPC"""
        for char_data in self.characters_data:
            char_id = char_data.get("id")
            if char_id:
                self.npcs[char_id] = NPCAgent(char_data)
    
    def get_npc(self, npc_id: str) -> Optional[NPCAgent]:
        """获取指定NPC"""
        return self.npcs.get(npc_id)
    
    def get_all_npcs(self) -> Dict[str, NPCAgent]:
        """获取所有NPC"""
        return self.npcs
    
    def update_npc_states(self, updates: List[Dict[str, Any]]):
        """批量更新NPC状态"""
        for update in updates:
            npc_id = update.get("npc_id")
            npc = self.get_npc(npc_id)
            if npc:
                npc.update_state(
                    location=update.get("current_location"),
                    activity=update.get("current_activity"),
                    mood=update.get("mood")
                )

