"""
蚂蚁A (npc_013) - 角色专属Agent
自动生成于 2025-12-02 13:24:51

提示词文件: prompts/online/npc_prompt/npc_013_蚂蚁A_prompt.txt
"""
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.llm_factory import get_llm
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger("npc_013", "npc_013.log")


class Npc013Agent:
    """
    蚂蚁A 角色专属Agent
    
    角色ID: npc_013
    角色名称: 蚂蚁A
    
    提示词: 从 prompts/online/npc_prompt/npc_013_蚂蚁A_prompt.txt 读取
    角色数据已预填充到提示词文件中，运行时只需填充剧本相关变量
    """
    
    CHARACTER_ID = "npc_013"
    CHARACTER_NAME = "蚂蚁A"
    PROMPT_FILE = "npc_prompt/npc_013_蚂蚁A_prompt.txt"  # 专属提示词文件
    
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
        
        # 加载专属提示词文件（角色数据已预填充）
        self.prompt_template = self._load_prompt_template()
        
        logger.info(f"✅ {self.CHARACTER_NAME} 初始化完成")
        logger.info(f"   📝 提示词文件: {self.PROMPT_FILE}")
    
    def _load_prompt_template(self) -> str:
        """加载专属提示词文件"""
        prompt_file = settings.PROMPTS_DIR / "online" / self.PROMPT_FILE
        if not prompt_file.exists():
            logger.warning(f"⚠️ 专属提示词文件不存在，使用通用模板: {prompt_file}")
            prompt_file = settings.PROMPTS_DIR / "online" / "npc_system.txt"
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
        """
        构建完整的提示词
        
        角色数据已在提示词文件中预填充，这里只需填充剧本相关的动态变量
        """
        mission = self.current_script.get("mission", {}) if self.current_script else {}
        
        # 从场景记忆板获取对话历史
        if self.scene_memory:
            dialogue_history = self.scene_memory.get_dialogue_for_prompt(limit=10)
        else:
            dialogue_history = "（这是对话的开始）"
        
        # 格式化关键话题
        key_topics = mission.get("key_topics", [])
        key_topics_str = ", ".join(key_topics) if isinstance(key_topics, list) else str(key_topics)
        
        # 只填充剧本相关的动态变量（角色数据已在提示词文件中）
        filled_prompt = self.prompt_template
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
def create_agent() -> Npc013Agent:
    """创建 蚂蚁A Agent实例"""
    return Npc013Agent()
