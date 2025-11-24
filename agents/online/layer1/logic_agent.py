"""
逻辑审查官 (Logic Validator)
独立中间件，负责审核输入输出的逻辑一致性，防止幻觉和世界观冲突
"""
import json
from typing import Dict, Any, Optional
from pathlib import Path
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from utils.llm_factory import get_llm
from utils.logger import setup_logger
from config.settings import settings
from agents.message_protocol import (
    Message, AgentRole, MessageType, ValidationResult,
    create_validation_response
)

logger = setup_logger("Logic", "logic.log")


class LogicValidator:
    """
    逻辑审查官Agent
    基于LLM的验证系统
    """
    
    def __init__(self):
        """初始化逻辑审查官"""
        logger.info("🔍 初始化逻辑审查官...")
        
        # 创建LLM实例（使用较低温度以提高判断准确性）
        self.llm = get_llm(temperature=0.3)
        
        # 加载系统提示词
        self.system_prompt = self._load_system_prompt()
        
        # 创建处理链
        self.chain = self._build_chain()
        
        # 世界观缓存
        self.world_rules: Optional[Dict[str, Any]] = None
        
        logger.info("✅ 逻辑审查官初始化完成")
    
    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        prompt_file = settings.PROMPTS_DIR / "online" / "logic_system.txt"
        
        if not prompt_file.exists():
            logger.error(f"❌ 未找到提示词文件: {prompt_file}")
            raise FileNotFoundError(f"提示词文件不存在: {prompt_file}")
        
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        logger.info(f"✅ 成功加载提示词: {prompt_file.name}")
        return content
    
    def _build_chain(self):
        """构建LangChain处理链"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", """请审核以下内容：

【世界观设定】
{world_context}

【待审核内容类型】
{content_type}

【待审核内容】
{content}

请严格按照JSON格式返回验证结果。""")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        return chain
    
    def set_world_rules(self, world_data: Dict[str, Any]):
        """
        设置世界观规则
        
        Args:
            world_data: Genesis数据中的world字段
        """
        self.world_rules = world_data
        logger.info(f"✅ 世界观规则已加载: {world_data.get('title')}")
    
    def validate_user_input(
        self,
        user_input: str,
        context: Dict[str, Any]
    ) -> ValidationResult:
        """
        验证用户输入
        
        Args:
            user_input: 用户的输入内容
            context: 当前游戏上下文
        
        Returns:
            验证结果
        """
        logger.info(f"🔍 审核用户输入: {user_input[:50]}...")
        
        # 构建世界观描述
        world_context = self._build_world_context(context)
        
        # 调用LLM进行验证
        try:
            response = self.chain.invoke({
                "world_context": world_context,
                "content_type": "用户输入",
                "content": user_input
            })
            
            # 解析结果
            result = self._parse_validation_result(response)
            
            if result.is_valid:
                logger.info("✅ 用户输入验证通过")
            else:
                logger.warning(f"❌ 用户输入被拒绝: {', '.join(result.errors)}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 验证过程出错: {e}", exc_info=True)
            # 出错时默认通过，避免阻塞游戏流程
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=["验证系统暂时不可用，已默认通过"],
                validated_content=user_input
            )
    
    def validate_ai_output(
        self,
        ai_output: str,
        context: Dict[str, Any]
    ) -> ValidationResult:
        """
        验证AI生成的输出
        
        Args:
            ai_output: AI生成的内容
            context: 当前游戏上下文（包含角色人设等）
        
        Returns:
            验证结果
        """
        logger.info(f"🔍 审核AI输出: {ai_output[:50]}...")
        
        # 构建上下文（包含角色人设）
        world_context = self._build_world_context(context, include_character=True)
        
        try:
            response = self.chain.invoke({
                "world_context": world_context,
                "content_type": "AI生成内容",
                "content": ai_output
            })
            
            result = self._parse_validation_result(response)
            
            if result.is_valid:
                logger.info("✅ AI输出验证通过")
            else:
                logger.warning(f"❌ AI输出被拒绝: {', '.join(result.errors)}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 验证过程出错: {e}", exc_info=True)
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=["验证系统暂时不可用，已默认通过"],
                validated_content=ai_output
            )
    
    def _build_world_context(
        self,
        context: Dict[str, Any],
        include_character: bool = False
    ) -> str:
        """构建世界观描述文本"""
        parts = []
        
        # 基础世界观
        if self.world_rules:
            parts.append(f"【世界名称】{self.world_rules.get('title', '未知')}")
            parts.append(f"【世界类型】{self.world_rules.get('genre', '未知')}")
            parts.append(f"【时代背景】{self.world_rules.get('time_period', '未知')}")
            
            rules = self.world_rules.get('world_rules', [])
            if rules:
                if isinstance(rules, list):
                    parts.append(f"【核心规则】\n" + "\n".join(f"- {rule}" for rule in rules))
                else:
                    parts.append(f"【核心规则】{rules}")
        
        # 当前场景上下文
        if "current_location" in context:
            parts.append(f"【当前位置】{context['current_location']}")
        
        if "current_time" in context:
            parts.append(f"【当前时间】{context['current_time']}")
        
        # 角色信息（用于AI输出验证）
        if include_character and "character_data" in context:
            char = context["character_data"]
            parts.append(f"【角色人设】")
            parts.append(f"姓名: {char.get('name', '未知')}")
            parts.append(f"性格: {', '.join(char.get('personality', []))}")
            parts.append(f"背景: {char.get('background', '未知')}")
        
        return "\n".join(parts)
    
    def _parse_validation_result(self, response: str) -> ValidationResult:
        """解析LLM返回的验证结果"""
        # 提取JSON（去除可能的markdown格式）
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
            
            return ValidationResult(
                is_valid=data.get("is_valid", False),
                errors=data.get("errors", []),
                warnings=data.get("warnings", []),
                validated_content=data.get("validated_content")
            )
        except json.JSONDecodeError as e:
            logger.error(f"❌ 解析验证结果失败: {e}")
            logger.error(f"原始响应: {response[:200]}...")
            
            # 如果解析失败，尝试启发式判断
            if "false" in response.lower() or "错误" in response or "拒绝" in response:
                return ValidationResult(
                    is_valid=False,
                    errors=["验证失败（解析错误）"],
                    warnings=[],
                    validated_content=None
                )
            else:
                return ValidationResult(
                    is_valid=True,
                    errors=[],
                    warnings=["验证结果解析异常，已默认通过"],
                    validated_content=None
                )
    
    def handle_message(self, message: Message) -> Optional[Message]:
        """
        处理消息（OS调用的接口）
        
        Args:
            message: 收到的消息
        
        Returns:
            响应消息
        """
        if message.message_type != MessageType.VALIDATION_REQUEST:
            logger.warning(f"⚠️  收到非验证请求消息: {message.message_type}")
            return None
        
        # 提取载荷
        content = message.payload.get("content", "")
        context = message.payload.get("context", {})
        content_type = message.payload.get("content_type", "user_input")
        
        # 执行验证
        if content_type == "user_input":
            result = self.validate_user_input(content, context)
        elif content_type == "ai_output":
            result = self.validate_ai_output(content, context)
        else:
            logger.warning(f"⚠️  未知的内容类型: {content_type}")
            result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # 创建响应消息
        response = create_validation_response(
            is_valid=result.is_valid,
            errors=result.errors,
            warnings=result.warnings,
            validated_content=result.validated_content
        )
        
        # 修改响应目标为原发送者
        response.to_agent = message.from_agent
        
        return response

