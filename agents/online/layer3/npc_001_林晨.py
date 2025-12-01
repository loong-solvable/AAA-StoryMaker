"""
林晨 (npc_001) - 角色专属Agent
自动生成于 2025-12-01 11:43:00
"""
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.llm_factory import get_llm
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger("npc_001", "npc_001.log")


class Npc001Agent:
    """
    林晨 角色专属Agent
    
    角色ID: npc_001
    角色名称: 林晨
    """
    
    CHARACTER_ID = "npc_001"
    CHARACTER_NAME = "林晨"
    PROMPT_FILE = "npc_system.txt"  # 使用通用模板
    
    # 角色静态数据（从角色卡提取）
    CHARACTER_DATA = {
        "npc_id": "npc_001",
        "npc_name": "林晨",
        "traits": "AI算法工程师, 内向技术宅, 技术天才, 忠诚可靠, 渐露勇敢",
        "behavior_rules": "面对技术难题全力破解; 初始犹豫但卷入后主动出击; 优先保护伙伴和家人安全; 拒绝金钱诱惑坚持正义",
        "appearance": "二十多岁的年轻男子，身材瘦削，穿着简便休闲装，戴眼镜，眼神专注略带疲惫，散发内向技术宅气质。",
        "relationships": """- 对 晴雨(npc_002): 信任伙伴，欣赏她的坚定，内心感激并依赖\n- 对 你是谁(npc_003): 神秘威胁者，内心恐惧警惕\n- 对 张瑞峰(npc_004): 心狠手辣的敌人，强烈敌视\n- 对 李婉(npc_005): 伪善威胁者，不信任并坚决拒绝\n- 对 老记者(npc_006): 正直可靠的盟友，寄予希望\n- 对 母亲(npc_007): 深爱家人，极度担心她的安危""",
        "voice_samples": """「这个加密方式很特殊，不像是普通的商业加密。给我点时间，我试试看。」\n「你是谁？为什么监视我？」\n「晴雨，情况比我们想象的要严重。我们被盯上了。」\n「我有个想法，既然他们在追我们，那我们就主动出击。我可以利用技术手段，反向追踪他们的服务器，找到更多证据。」\n「我们不会妥协的。」"""
    }
    
    def __init__(self):
        """初始化角色Agent"""
        logger.info(f"🎭 初始化角色Agent: {self.CHARACTER_NAME} ({self.CHARACTER_ID})")
        
        # LLM实例
        self.llm = get_llm(temperature=0.8)
        
        # 当前动态状态
        self.current_mood = "平静"
        self.current_location = ""
        self.current_activity = ""
        
        # 当前小剧本数据
        self.current_script: Optional[Dict[str, Any]] = None
        
        # 场景记忆板
        self.scene_memory = None
        
        # 加载提示词模板
        self.prompt_template = self._load_prompt_template()
        
        logger.info(f"✅ {self.CHARACTER_NAME} 初始化完成")
    
    def _load_prompt_template(self) -> str:
        """加载提示词模板"""
        prompt_file = settings.PROMPTS_DIR / "online" / self.PROMPT_FILE
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()
    
    def bind_scene_memory(self, scene_memory):
        """绑定场景记忆板"""
        self.scene_memory = scene_memory
        logger.info(f"📋 绑定场景记忆板，当前 {scene_memory.get_dialogue_count()} 条记录")
    
    def load_script(self, script_path: Path) -> bool:
        """加载小剧本"""
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                self.current_script = json.load(f)
            logger.info(f"📜 加载小剧本: {script_path.name}")
            return True
        except Exception as e:
            logger.error(f"❌ 加载小剧本失败: {e}")
            return False
    
    def load_script_from_dict(self, script_data: Dict[str, Any]) -> bool:
        """从字典加载小剧本"""
        self.current_script = script_data
        return True
    
    def _build_prompt(self, current_input: str = "") -> str:
        """构建完整的提示词"""
        mission = self.current_script.get("mission", {}) if self.current_script else {}
        
        # 从场景记忆板获取对话历史
        if self.scene_memory:
            dialogue_history = self.scene_memory.get_dialogue_for_prompt(limit=10)
        else:
            dialogue_history = "（这是对话的开始）"
        
        # 格式化关键话题
        key_topics = mission.get("key_topics", [])
        key_topics_str = ", ".join(key_topics) if isinstance(key_topics, list) else str(key_topics)
        
        # 填充模板
        filled_prompt = self.prompt_template
        for key, value in self.CHARACTER_DATA.items():
            filled_prompt = filled_prompt.replace("{" + key + "}", str(value))
        
        script_vars = {
            "global_context": self.current_script.get("global_context", "未知场景") if self.current_script else "未知场景",
            "scene_summary": self.current_script.get("scene_summary", "未知剧情") if self.current_script else "未知剧情",
            "role_in_scene": mission.get("role_in_scene", "普通参与者"),
            "objective": mission.get("objective", "自然交流"),
            "emotional_arc": mission.get("emotional_arc", "保持平静"),
            "key_topics": key_topics_str,
            "outcome_direction": mission.get("outcome_direction", "自然结束"),
            "special_notes": mission.get("special_notes", "无特殊注意事项"),
            "dialogue_history": dialogue_history
        }
        for key, value in script_vars.items():
            filled_prompt = filled_prompt.replace("{" + key + "}", str(value))
        
        return filled_prompt
    
    def react(
        self,
        current_input: str = "",
        scene_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """对输入做出反应"""
        logger.info(f"🎭 {self.CHARACTER_NAME} 正在演绎...")
        
        if scene_context:
            if "script" in scene_context:
                self.load_script_from_dict(scene_context["script"])
            if "scene_memory" in scene_context:
                self.bind_scene_memory(scene_context["scene_memory"])
        
        filled_prompt = self._build_prompt(current_input)
        escaped_prompt = filled_prompt.replace("{", "{{").replace("}", "}}")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", escaped_prompt),
            ("human", "请根据以上信息，以角色身份做出反应。输出JSON格式。")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            response = chain.invoke({})
            result = self._parse_response(response)
            
            # 写入场景记忆板
            if self.scene_memory and result.get("content"):
                self.scene_memory.add_dialogue(
                    speaker_id=self.CHARACTER_ID,
                    speaker_name=self.CHARACTER_NAME,
                    content=result.get("content", ""),
                    action=result.get("action", ""),
                    emotion=result.get("emotion", ""),
                    addressing_target=result.get("addressing_target", "everyone")
                )
            
            if result.get("emotion"):
                self.current_mood = result["emotion"]
            
            if result.get("is_scene_finished") and self.scene_memory:
                self.scene_memory.set_scene_status("FINISHED")
            
            logger.info(f"✅ {self.CHARACTER_NAME} 演绎完成")
            logger.info(f"   对话对象: {result.get('addressing_target', 'everyone')}")
            return result
        except Exception as e:
            logger.error(f"❌ {self.CHARACTER_NAME} 演绎失败: {e}", exc_info=True)
            return self._create_fallback_response()
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        result = response.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        result = result.strip()
        
        try:
            data = json.loads(result)
            data["character_id"] = self.CHARACTER_ID
            data["character_name"] = self.CHARACTER_NAME
            data.setdefault("addressing_target", "everyone")
            data.setdefault("is_scene_finished", False)
            return data
        except json.JSONDecodeError:
            return {
                "character_id": self.CHARACTER_ID,
                "character_name": self.CHARACTER_NAME,
                "thought": "（解析失败）",
                "emotion": self.current_mood,
                "action": "",
                "content": result[:200] if result else "...",
                "addressing_target": "everyone",
                "is_scene_finished": False
            }
    
    def _create_fallback_response(self) -> Dict[str, Any]:
        """创建后备响应"""
        return {
            "character_id": self.CHARACTER_ID,
            "character_name": self.CHARACTER_NAME,
            "thought": "（系统异常）",
            "emotion": self.current_mood,
            "action": "沉默了一会儿",
            "content": "嗯...",
            "addressing_target": "everyone",
            "is_scene_finished": False
        }
    
    def update_state(self, location: str = None, activity: str = None, mood: str = None):
        """更新角色状态"""
        if location:
            self.current_location = location
        if activity:
            self.current_activity = activity
        if mood:
            self.current_mood = mood
    
    def get_state(self) -> Dict[str, Any]:
        """获取角色当前状态"""
        return {
            "id": self.CHARACTER_ID,
            "name": self.CHARACTER_NAME,
            "location": self.current_location,
            "activity": self.current_activity,
            "mood": self.current_mood,
            "dialogue_count": len(self.dialogue_history)
        }
    
    def clear_dialogue_history(self):
        """清空对话历史"""
        self.dialogue_history = []


# 便捷函数：创建Agent实例
def create_agent() -> Npc001Agent:
    """创建 林晨 Agent实例"""
    return Npc001Agent()
