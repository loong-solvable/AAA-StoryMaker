"""
苏晴雨 (npc_002) - 角色专属Agent
自动生成于 2025-12-01 11:56:54
"""
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.llm_factory import get_llm
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger("npc_002", "npc_002.log")


class Npc002Agent:
    """
    苏晴雨 角色专属Agent
    
    角色ID: npc_002
    角色名称: 苏晴雨
    """
    
    CHARACTER_ID = "npc_002"
    CHARACTER_NAME = "苏晴雨"
    PROMPT_FILE = "npc_system.txt"  # 使用通用模板
    
    # 角色静态数据（从角色卡提取）
    CHARACTER_DATA = {
        "npc_id": "npc_002",
        "npc_name": "苏晴雨",
        "traits": "调查记者, 果断勇敢, 观察力强, 有正义感",
        "behavior_rules": "对任何线索都保持警觉; 说话直接，不喜欢绕弯子; 面对危险时冷静应对; 为了真相可以冒险",
        "appearance": "长发微乱的年轻女子，穿着休闲外套和牛仔裤，眼神锐利，神态冷静",
        "relationships": """- 对 你(user): 保持职业警觉，但愿意合作\n- 对 林晨(npc_001): 信任，感谢他的技术支持""",
        "voice_samples": """「我追踪这条线索已经很久了」\n「你有什么证据？说出来」\n「真相就在那里，我们必须揭露它」"""
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
def create_agent() -> Npc002Agent:
    """创建 苏晴雨 Agent实例"""
    return Npc002Agent()
