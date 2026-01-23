"""
增强日志工具模块

特性：
- 彩色控制台输出
- 分离的日志文件（普通日志 + 错误专用日志）
- 毫秒级时间戳
- 自动堆栈跟踪
- 上下文追踪（当前场景、角色等）
- LLM 调用日志记录
"""
import logging
import colorlog
import traceback
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from contextlib import contextmanager
from functools import wraps

from config.settings import settings


# ============================================================
# 全局上下文追踪
# ============================================================

class LogContext:
    """日志上下文管理器 - 追踪当前操作的上下文信息"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._context = {}
        return cls._instance
    
    def set(self, key: str, value: Any):
        """设置上下文变量"""
        self._context[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文变量"""
        return self._context.get(key, default)
    
    def clear(self, key: str = None):
        """清除上下文变量"""
        if key:
            self._context.pop(key, None)
        else:
            self._context.clear()
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有上下文"""
        return self._context.copy()
    
    def format_context(self) -> str:
        """格式化上下文为字符串"""
        if not self._context:
            return ""
        parts = [f"{k}={v}" for k, v in self._context.items()]
        return f" [{', '.join(parts)}]"


# 全局上下文实例
log_context = LogContext()


@contextmanager
def log_operation(operation: str, **kwargs):
    """
    上下文管理器：标记当前操作
    
    用法:
        with log_operation("处理角色对话", character="林晨", scene_id=1):
            # 在此范围内的所有日志都会包含上下文信息
            logger.info("开始处理")
    """
    old_context = log_context.get_all()
    log_context.set("operation", operation)
    for key, value in kwargs.items():
        log_context.set(key, value)
    
    try:
        yield
    finally:
        log_context.clear()
        for key, value in old_context.items():
            log_context.set(key, value)


# ============================================================
# 增强的日志格式化器
# ============================================================

class EnhancedFormatter(logging.Formatter):
    """增强的日志格式化器 - 添加上下文信息和堆栈跟踪"""
    
    def format(self, record):
        # 添加上下文信息
        context_str = log_context.format_context()
        if context_str:
            record.msg = f"{record.msg}{context_str}"
        
        # 对于错误级别，自动添加堆栈跟踪
        if record.levelno >= logging.ERROR and not record.exc_info:
            # 检查是否在异常处理中
            exc_info = sys.exc_info()
            if exc_info[0] is not None:
                record.exc_info = exc_info
        
        return super().format(record)


class ColoredEnhancedFormatter(colorlog.ColoredFormatter):
    """彩色增强格式化器"""
    
    def format(self, record):
        context_str = log_context.format_context()
        if context_str:
            record.msg = f"{record.msg}{context_str}"
        return super().format(record)


# ============================================================
# Logger 设置函数
# ============================================================

def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """
    配置并返回增强的logger实例
    
    Args:
        name: logger名称
        log_file: 日志文件名（可选，会保存到logs目录）
    
    Returns:
        配置好的logger实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 避免重复添加handler (清除现有handler)
    if logger.handlers:
        logger.handlers.clear()
    
    # 禁止向上传播，防止根logger重复记录
    logger.propagate = False
    
    settings.ensure_directories()
    
    # 1. 彩色控制台输出
    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = ColoredEnhancedFormatter(
        '%(log_color)s[%(asctime)s.%(msecs)03d] [%(name)s] [%(levelname)s]%(reset)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # 2. 普通日志文件输出（如果指定）
    if log_file:
        file_path = settings.LOGS_DIR / log_file
        file_handler = logging.FileHandler(file_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_format = EnhancedFormatter(
            '[%(asctime)s.%(msecs)03d] [%(name)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    # 3. 错误专用日志文件（自动添加）
    error_log_path = settings.LOGS_DIR / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
    error_handler = logging.FileHandler(error_log_path, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_format = EnhancedFormatter(
        '\n{"timestamp": "%(asctime)s.%(msecs)03d", "logger": "%(name)s", "level": "%(levelname)s", '
        '"file": "%(filename)s", "line": %(lineno)d, "function": "%(funcName)s", '
        '"message": "%(message)s"}\n%(exc_text)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    error_handler.setFormatter(error_format)
    logger.addHandler(error_handler)
    
    return logger


def mute_console_handlers() -> None:
    root = logging.getLogger()
    logger_dict = logging.root.manager.loggerDict

    for logger in logger_dict.values():
        if isinstance(logger, logging.PlaceHolder):
            continue
        for handler in list(logger.handlers):
            if isinstance(handler, logging.StreamHandler):
                logger.removeHandler(handler)
        logger.propagate = True


# ============================================================
# LLM 调用日志工具
# ============================================================

class LLMCallLogger:
    """LLM 调用日志记录器"""
    
    def __init__(self, logger_name: str = "LLMCalls"):
        self.logger = setup_logger(logger_name, f"llm_calls_{datetime.now().strftime('%Y%m%d')}.log")
        self._call_count = 0
    
    def log_call(
        self,
        operation: str,
        prompt_preview: str = "",
        response_preview: str = "",
        tokens_used: int = 0,
        duration_ms: float = 0,
        success: bool = True,
        error: str = ""
    ):
        """
        记录一次 LLM 调用
        
        Args:
            operation: 操作名称（如 "剧本拆分", "NPC对话"）
            prompt_preview: 提示词预览（前200字符）
            response_preview: 响应预览（前200字符）
            tokens_used: 使用的 token 数
            duration_ms: 耗时（毫秒）
            success: 是否成功
            error: 错误信息（如果失败）
        """
        self._call_count += 1
        
        log_data = {
            "call_id": self._call_count,
            "operation": operation,
            "prompt_preview": prompt_preview[:200] if prompt_preview else "",
            "response_preview": response_preview[:200] if response_preview else "",
            "tokens_used": tokens_used,
            "duration_ms": round(duration_ms, 2),
            "success": success,
            "context": log_context.get_all()
        }
        
        if error:
            log_data["error"] = error
        
        level = logging.INFO if success else logging.ERROR
        self.logger.log(level, json.dumps(log_data, ensure_ascii=False, indent=None))
        
        if not success:
            self.logger.error(f"❌ LLM 调用失败 [{operation}]: {error}")


# 全局 LLM 调用日志实例
llm_logger = LLMCallLogger()


def log_llm_call(operation: str):
    """
    装饰器：自动记录 LLM 调用
    
    用法:
        @log_llm_call("剧本拆分")
        def call_llm_for_script(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                llm_logger.log_call(
                    operation=operation,
                    response_preview=str(result)[:200] if result else "",
                    duration_ms=duration_ms,
                    success=True
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                llm_logger.log_call(
                    operation=operation,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e)
                )
                
                raise
        
        return wrapper
    return decorator


# ============================================================
# 便捷函数
# ============================================================

def log_exception(logger: logging.Logger, message: str, exc: Exception = None):
    """
    便捷函数：记录异常，自动包含堆栈跟踪
    
    用法:
        try:
            ...
        except Exception as e:
            log_exception(logger, "处理失败", e)
    """
    if exc:
        logger.error(f"{message}: {type(exc).__name__}: {exc}")
        logger.debug(f"堆栈跟踪:\n{traceback.format_exc()}")
    else:
        logger.error(message)
        logger.debug(f"当前堆栈:\n{traceback.format_stack()}")


def log_with_data(logger: logging.Logger, level: int, message: str, data: Dict[str, Any]):
    """
    便捷函数：记录带有结构化数据的日志
    
    用法:
        log_with_data(logger, logging.INFO, "处理完成", {"count": 10, "duration": 1.5})
    """
    data_str = json.dumps(data, ensure_ascii=False, default=str)
    logger.log(level, f"{message} | data={data_str}")


# ============================================================
# 默认 Logger
# ============================================================

# 创建默认logger
default_logger = setup_logger(
    "StoryMaker",
    f"story_maker_{datetime.now().strftime('%Y%m%d')}.log"
)


