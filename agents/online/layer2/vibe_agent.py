"""
氛围感受者 (Atmosphere Creator)
美工/摄影师，负责生成沉浸式的环境描写
"""
import json
from typing import Dict, Any, Optional
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from utils.llm_factory import get_llm
from utils.logger import setup_logger
from config.settings import settings
from agents.message_protocol import Message, AgentRole, MessageType, GeneratedContent

logger = setup_logger("Vibe", "vibe.log")


class AtmosphereCreator:
    """
    氛围感受者Agent
    创造沉浸式的环境氛围
    """
    
    def __init__(self, genesis_data: Dict[str, Any]):
        """
        初始化氛围感受者
        
        Args:
            genesis_data: Genesis世界数据
        """
        logger.info("🎨 初始化氛围感受者...")
        
        # LLM实例（高温度以增加创造性）
        self.llm = get_llm(temperature=0.9)
        
        # Genesis数据
        self.genesis_data = genesis_data
        self.locations = genesis_data.get("locations", [])
        self.world_info = genesis_data.get("world", {})
        
        # 加载提示词
        self.system_prompt = self._load_system_prompt()
        
        # 构建链
        self.chain = self._build_chain()
        
        # 描写历史（避免重复）
        self.description_history: List[str] = []
        
        logger.info("✅ 氛围感受者初始化完成")
    
    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        prompt_file = settings.PROMPTS_DIR / "online" / "vibe_system.txt"
        
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()
    
    def _build_chain(self):
        """构建处理链"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", """请创作环境氛围描写：

【世界类型】
{genre}

【当前场所】
位置ID：{location_id}
位置名称：{location_name}
位置描述：{location_description}

【场景指令】
主题情绪：{mood}
基调：{tone}
焦点：{focus}
要求的感官细节：{sensory_requirements}

【时间与天气】
时间：{current_time}
天气：{weather}

【避免重复】
最近的描写片段（请避免类似表达）：
{recent_descriptions}

请创作富有感染力的氛围描写，返回JSON格式。""")
        ])
        
        return prompt | self.llm | StrOutputParser()
    
    def create_atmosphere(
        self,
        location_id: str,
        director_instruction: Dict[str, Any],
        current_time: str = "",
        weather: str = "晴朗"
    ) -> Dict[str, Any]:
        """
        创作环境氛围
        
        Args:
            location_id: 地点ID
            director_instruction: 导演指令
            current_time: 当前时间
            weather: 天气
        
        Returns:
            氛围描写数据
        """
        logger.info(f"🎨 创作氛围描写: {location_id}")
        
        # 获取地点信息
        location_data = self._get_location_data(location_id)
        
        # 提取指令参数
        params = director_instruction.get("parameters", {})
        
        try:
            response = self.chain.invoke({
                "genre": self.world_info.get("genre", "现代都市"),
                "location_id": location_id,
                "location_name": location_data.get("name", "未知地点"),
                "location_description": location_data.get("description", ""),
                "mood": params.get("emotional_tone", "平静"),
                "tone": director_instruction.get("tone", "日常"),
                "focus": params.get("focus", "整体环境"),
                "sensory_requirements": ", ".join(params.get("sensory_details", [])),
                "current_time": current_time or "当前",
                "weather": weather,
                "recent_descriptions": self._format_recent_descriptions()
            })
            
            # 解析结果
            atmosphere = self._parse_atmosphere(response)
            
            # 记录到历史
            desc = atmosphere.get("atmosphere_description", "")
            if desc:
                self.description_history.append(desc[:100])  # 保存前100字
                if len(self.description_history) > 5:
                    self.description_history.pop(0)
            
            logger.info(f"✅ 氛围描写完成")
            logger.info(f"   - 情绪: {', '.join(atmosphere.get('mood_keywords', []))}")
            
            return atmosphere
            
        except Exception as e:
            logger.error(f"❌ 氛围创作失败: {e}", exc_info=True)
            return self._create_minimal_atmosphere(location_data)
    
    def _get_location_data(self, location_id: str) -> Dict[str, Any]:
        """获取地点数据"""
        for loc in self.locations:
            if loc.get("id") == location_id:
                return loc
        
        return {
            "id": location_id,
            "name": "未知地点",
            "description": "一个普通的场所"
        }
    
    def _format_recent_descriptions(self) -> str:
        """格式化最近的描写"""
        if not self.description_history:
            return "无"
        
        return "\n".join([f"- {desc}..." for desc in self.description_history[-3:]])
    
    def _parse_atmosphere(self, response: str) -> Dict[str, Any]:
        """解析氛围描写"""
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
            logger.error(f"❌ 解析氛围描写失败: {e}")
            logger.error(f"原始响应: {response[:200]}...")
            return {
                "atmosphere_description": "环境很普通。",
                "sensory_details": {},
                "mood_keywords": ["平静"],
                "focus_elements": []
            }
    
    def _create_minimal_atmosphere(self, location_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建最小氛围描写（出错时使用）"""
        location_name = location_data.get("name", "这里")
        
        return {
            "atmosphere_description": f"{location_name}的环境很普通，没有什么特别之处。",
            "sensory_details": {
                "visual": [f"{location_name}的布局"],
                "auditory": ["环境音"],
                "olfactory": [],
                "tactile": [],
                "emotional": ["平静"]
            },
            "mood_keywords": ["平静", "普通"],
            "focus_elements": ["整体环境"]
        }
    
    def handle_message(self, message: Message) -> Optional[Message]:
        """处理消息（OS接口）"""
        if message.message_type == MessageType.GENERATION_REQUEST:
            payload = message.payload
            
            if payload.get("content_type") == "atmosphere":
                atmosphere = self.create_atmosphere(
                    location_id=payload.get("location_id", ""),
                    director_instruction=payload.get("instruction", {}),
                    current_time=payload.get("current_time", ""),
                    weather=payload.get("weather", "晴朗")
                )
                
                # 创建响应
                from agents.message_protocol import create_message
                
                content = GeneratedContent(
                    content_type="description",
                    content=atmosphere.get("atmosphere_description", ""),
                    emotion=", ".join(atmosphere.get("mood_keywords", []))
                )
                
                return create_message(
                    from_agent=AgentRole.VIBE,
                    to_agent=message.from_agent,
                    message_type=MessageType.GENERATION_RESPONSE,
                    payload=content.dict()
                )
        
        return None

