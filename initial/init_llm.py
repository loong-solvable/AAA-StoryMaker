"""
LLM初始化模块
负责创建和配置LLM实例
"""
from typing import Optional
from langchain_core.language_models.base import BaseLanguageModel
from utils.llm_factory import get_llm
from utils.logger import setup_logger

logger = setup_logger("InitLLM")


def initialize_llm(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> BaseLanguageModel:
    """
    初始化LLM实例
    
    Args:
        provider: LLM提供商 (zhipu/openai)，默认从配置读取
        model_name: 模型名称，默认从配置读取
        temperature: 温度参数，默认从配置读取
        max_tokens: 最大token数，默认从配置读取
    
    Returns:
        LLM实例
    """
    logger.info("🤖 开始初始化LLM...")
    
    try:
        llm = get_llm(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
        logger.info("✅ LLM初始化成功")
        return llm
    except Exception as e:
        logger.error(f"❌ LLM初始化失败: {e}")
        raise

