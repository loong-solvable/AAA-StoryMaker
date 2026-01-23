"""
LLM工厂模块
支持多种LLM提供商，遵循低耦合原则
支持: zhipu(智谱清言), openai, openrouter
"""
from typing import Optional
from langchain_core.language_models import BaseLanguageModel
from config.settings import settings
from utils.logger import setup_logger
from utils.custom_zhipuai import CustomChatZhipuAI

logger = setup_logger("LLMFactory")

# 优先使用新版 langchain_openai，如果不可用则回退到旧版
try:
    from langchain_openai import ChatOpenAI
    logger.info("✅ 使用 langchain_openai.ChatOpenAI（推荐）")
except ImportError:
    from langchain_community.chat_models import ChatOpenAI
    logger.warning("⚠️ langchain_openai 未安装，使用旧版 langchain_community.ChatOpenAI")
    logger.warning("   建议运行: pip install langchain-openai")


class LLMFactory:
    """LLM工厂类，用于创建不同提供商的LLM实例"""
    
    @staticmethod
    def create_llm(
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None
    ) -> BaseLanguageModel:
        """
        创建LLM实例
        
        Args:
            provider: LLM提供商 (zhipu/openai/openrouter)，默认从配置读取
            model_name: 模型名称，默认从配置读取
            temperature: 温度参数，默认从配置读取
            max_tokens: 最大token数，默认从配置读取
        
        Returns:
            LLM实例
        """
        provider = provider or settings.LLM_PROVIDER

        if provider == "mock":
            from utils.mock_llm import MockChatLLM

            logger.info("🧪 使用 MockChatLLM（离线/CI 模式）")
            return MockChatLLM()
        
        # OpenRouter使用专门的模型配置
        if provider == "openrouter":
            model_name = model_name or settings.OPENROUTER_MODEL
        else:
            model_name = model_name or settings.MODEL_NAME
            
        temperature = temperature if temperature is not None else settings.TEMPERATURE
        max_tokens = max_tokens or settings.MAX_TOKENS
        
        logger.info(f"🤖 正在创建LLM实例: provider={provider}, model={model_name}")
        
        try:
            if provider == "zhipu":
                return LLMFactory._create_zhipu(model_name, temperature, max_tokens, timeout)
            elif provider == "openai":
                return LLMFactory._create_openai(model_name, temperature, max_tokens, timeout, max_retries)
            elif provider == "openrouter":
                return LLMFactory._create_openrouter(model_name, temperature, max_tokens, timeout, max_retries)
            else:
                raise ValueError(f"不支持的LLM提供商: {provider}")
        except Exception as e:
            logger.error(f"❌ 创建LLM失败: {e}")
            raise
    
    @staticmethod
    def _create_zhipu(
        model_name: str,
        temperature: float,
        max_tokens: Optional[int],
        timeout: Optional[float]
    ) -> CustomChatZhipuAI:
        """创建智谱清言LLM（使用自定义类修复超时问题）"""
        if not settings.ZHIPU_API_KEY:
            raise ValueError("❌ 未配置ZHIPU_API_KEY，请检查.env文件")
        
        # 使用自定义的CustomChatZhipuAI类，修复原始类硬编码60秒超时的问题
        # 原始ChatZhipuAI在_generate方法中硬编码: httpx.Client(timeout=60)
        # 导致无法配置更长的超时时间
        
        logger.info(f"⏱️  使用自定义ChatZhipuAI，配置超时: 7200秒 (2小时)")
        
        # 构建参数字典
        request_timeout = timeout if timeout is not None else 7200.0
        params = {
            "model": model_name,
            "temperature": temperature,
            "api_key": settings.ZHIPU_API_KEY,
            "request_timeout": request_timeout,
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        
        return CustomChatZhipuAI(**params)
    
    @staticmethod
    def _create_openai(
        model_name: str,
        temperature: float,
        max_tokens: Optional[int],
        timeout: Optional[float],
        max_retries: Optional[int]
    ) -> ChatOpenAI:
        """创建OpenAI LLM"""
        if not settings.OPENAI_API_KEY:
            raise ValueError("❌ 未配置OPENAI_API_KEY，请检查.env文件")
        
        # 构建参数字典，如果 max_tokens 为 None 则不传递该参数
        params = {
            "model": model_name,
            "temperature": temperature,
            "api_key": settings.OPENAI_API_KEY,
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        if timeout is not None:
            params["timeout"] = timeout
        if max_retries is not None:
            params["max_retries"] = max_retries
        
        return ChatOpenAI(**params)
    
    @staticmethod
    def _create_openrouter(
        model_name: str,
        temperature: float,
        max_tokens: Optional[int],
        timeout: Optional[float],
        max_retries: Optional[int]
    ) -> ChatOpenAI:
        """
        创建OpenRouter LLM
        
        OpenRouter提供统一的API接入多种模型，兼容OpenAI API格式
        官方文档: https://openrouter.ai/docs
        """
        if not settings.OPENROUTER_API_KEY:
            raise ValueError("❌ 未配置OPENROUTER_API_KEY，请检查.env文件")
        
        logger.info(f"🌐 使用OpenRouter API: {settings.OPENROUTER_BASE_URL}")
        logger.info(f"📦 模型: {model_name}")
        
        # OpenRouter兼容OpenAI API，使用ChatOpenAI类即可
        # 需要设置base_url指向OpenRouter的API端点
        params = {
            "model": model_name,
            "temperature": temperature,
            "api_key": settings.OPENROUTER_API_KEY,
            "base_url": settings.OPENROUTER_BASE_URL,
            "default_headers": {
                "HTTP-Referer": "https://github.com/AAA-StoryMaker",  # 可选：用于OpenRouter统计
                "X-Title": "AAA-StoryMaker"  # 可选：应用名称
            },
        }
        params["timeout"] = timeout if timeout is not None else 7200
        if max_retries is not None:
            params["max_retries"] = max_retries
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        
        return ChatOpenAI(**params)


# 便捷函数
def get_llm(**kwargs) -> BaseLanguageModel:
    """获取LLM实例的便捷函数"""
    return LLMFactory.create_llm(**kwargs)
