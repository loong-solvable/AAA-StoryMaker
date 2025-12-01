"""
苏晴雨 (npc_002) - 角色专属Agent
自动生成于 2025-12-01 10:10:31
"""
import json
from typing import Dict, Any, Optional, List
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
    PROMPT_FILE = "npc_002_苏晴雨.txt"
    
    def __init__(self):
        """初始化角色Agent"""
        logger.info(f"🎭 初始化角色Agent: {self.CHARACTER_NAME} ({self.CHARACTER_ID})")
        
        # LLM实例
        self.llm = get_llm(temperature=0.8)
        
        # 当前动态状态
        self.current_mood = "平静"
        self.current_location = ""
        self.current_activity = ""
        
        # 加载专属提示词
        self.system_prompt = self._load_prompt()
        
        # 对话历史
        self.dialogue_history: List[str] = []
        
        logger.info(f"✅ {self.CHARACTER_NAME} 初始化完成")
    
    def _load_prompt(self) -> str:
        """加载角色专属提示词"""
        prompt_file = settings.PROMPTS_DIR / "online" / self.PROMPT_FILE
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()
    
    def react(
        self,
        script: str,
        scene_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        对剧本做出反应
        
        Args:
            script: 角色的小剧本
            scene_context: 场景上下文（可选）
        
        Returns:
            角色的反应
        """
        logger.info(f"🎭 {self.CHARACTER_NAME} 正在演绎...")
        
        # 填充提示词中的 {id_script} 占位符
        filled_prompt = self.system_prompt.replace("{id_script}", script)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", filled_prompt),
            ("human", "请根据剧本演绎你的角色。")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            response = chain.invoke({})
            
            # 解析响应
            result = self._parse_response(response)
            
            logger.info(f"✅ {self.CHARACTER_NAME} 演绎完成")
            return result
            
        except Exception as e:
            logger.error(f"❌ {self.CHARACTER_NAME} 演绎失败: {e}", exc_info=True)
            return self._create_fallback_response()
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        return {
            "character_id": self.CHARACTER_ID,
            "character_name": self.CHARACTER_NAME,
            "performance": response,
            "mood": self.current_mood
        }
    
    def _create_fallback_response(self) -> Dict[str, Any]:
        """创建后备响应"""
        return {
            "character_id": self.CHARACTER_ID,
            "character_name": self.CHARACTER_NAME,
            "performance": f"{self.CHARACTER_ID}发送\n（{self.CHARACTER_NAME}沉默了一会儿）\n{self.CHARACTER_ID}演绎完毕",
            "mood": self.current_mood
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
            "mood": self.current_mood
        }


# 便捷函数：创建Agent实例
def create_agent() -> Npc002Agent:
    """创建 苏晴雨 Agent实例"""
    return Npc002Agent()
