"""
异常处理模块 - 友好的错误提示

负责：
- 将技术异常转换为用户友好的提示
- 记录完整堆栈到日志文件
"""

import logging
from typing import Optional

from utils.logger import setup_logger

logger = setup_logger("ExceptionHandler", "exception_handler.log")


# 异常类型 → 友好提示映射
FRIENDLY_MESSAGES = {
    "APIConnectionError": "网络连接失败，请检查网络后重试",
    "RateLimitError": "请求过于频繁，请稍后再试",
    "JSONDecodeError": "数据解析异常，游戏将使用备用方案继续",
    "TimeoutError": "服务响应超时，正在重试...",
    "FileNotFoundError": "游戏数据缺失，请确认世界已正确构建",
    "PermissionError": "文件权限不足，请检查文件夹权限",
    "KeyboardInterrupt": "用户中断操作",
    "ConnectionError": "网络连接失败，请检查网络后重试",
    "AuthenticationError": "API 密钥无效，请检查配置",
}


def handle_exception(e: Exception, context: str = "") -> str:
    """
    处理异常，返回友好提示，同时记录完整堆栈到日志
    
    Args:
        e: 异常对象
        context: 异常发生的上下文（如"加载世界数据"）
    
    Returns:
        用户友好的错误提示字符串
    """
    error_type = type(e).__name__
    friendly_msg = FRIENDLY_MESSAGES.get(error_type, f"发生意外错误: {str(e)[:50]}")
    
    # 完整堆栈写入日志
    log_msg = f"[{context}] {error_type}: {e}" if context else f"{error_type}: {e}"
    logger.error(log_msg, exc_info=True)
    
    return f"[ERROR] {friendly_msg}\n   (详细信息已记录到 logs/ 目录)"


def get_friendly_message(error_type: str) -> Optional[str]:
    """获取指定错误类型的友好提示"""
    return FRIENDLY_MESSAGES.get(error_type)


def register_friendly_message(error_type: str, message: str) -> None:
    """注册新的错误类型友好提示"""
    FRIENDLY_MESSAGES[error_type] = message

