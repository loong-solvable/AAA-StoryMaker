"""
LLM工厂模块
支持多种LLM提供商，遵循低耦合原则
"""
from typing import Optional
from langchain_community.chat_models import ChatZhipuAI
from langchain_community.chat_models import ChatOpenAI
from langchain_core.language_models import BaseLanguageModel
from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger("LLMFactory")


class LLMFactory:
    """LLM工厂类，用于创建不同提供商的LLM实例"""
    
    @staticmethod
    def create_llm(
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> BaseLanguageModel:
        """
        创建LLM实例
        
        Args:
            provider: LLM提供商 (zhipu/openai/iflytek)，默认从配置读取
            model_name: 模型名称，默认从配置读取
            temperature: 温度参数，默认从配置读取
            max_tokens: 最大token数，默认从配置读取
        
        Returns:
            LLM实例
        """
        provider = provider or settings.LLM_PROVIDER
        model_name = model_name or settings.MODEL_NAME
        temperature = temperature if temperature is not None else settings.TEMPERATURE
        max_tokens = max_tokens or settings.MAX_TOKENS
        
        logger.info(f"🤖 正在创建LLM实例: provider={provider}, model={model_name}")
        
        try:
            if provider == "zhipu":
                return LLMFactory._create_zhipu(model_name, temperature, max_tokens)
            elif provider == "openai":
                return LLMFactory._create_openai(model_name, temperature, max_tokens)
            else:
                raise ValueError(f"不支持的LLM提供商: {provider}")
        except Exception as e:
            logger.error(f"❌ 创建LLM失败: {e}")
            raise
    
    @staticmethod
    def _create_zhipu(model_name: str, temperature: float, max_tokens: int) -> ChatZhipuAI:
        """创建智谱清言LLM"""
        if not settings.ZHIPU_API_KEY:
            raise ValueError("❌ 未配置ZHIPU_API_KEY，请检查.env文件")
        
        return ChatZhipuAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=settings.ZHIPU_API_KEY,
        )
    
    @staticmethod
    def _create_openai(model_name: str, temperature: float, max_tokens: int) -> ChatOpenAI:
        """创建OpenAI LLM"""
        if not settings.OPENAI_API_KEY:
            raise ValueError("❌ 未配置OPENAI_API_KEY，请检查.env文件")
        
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=settings.OPENAI_API_KEY,
        )


# 便捷函数
def get_llm(**kwargs) -> BaseLanguageModel:
    """获取LLM实例的便捷函数"""
    return LLMFactory.create_llm(**kwargs)

