"""
日志工具模块
提供彩色日志输出和文件持久化
"""
import logging
import colorlog
from pathlib import Path
from datetime import datetime
from config.settings import settings


def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """
    配置并返回logger实例
    
    Args:
        name: logger名称
        log_file: 日志文件名（可选，会保存到logs目录）
    
    Returns:
        配置好的logger实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 彩色控制台输出
    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = colorlog.ColoredFormatter(
        '%(log_color)s[%(asctime)s] [%(name)s] [%(levelname)s]%(reset)s %(message)s',
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
    
    # 文件输出（如果指定）
    if log_file:
        settings.ensure_directories()
        file_path = settings.LOGS_DIR / log_file
        file_handler = logging.FileHandler(file_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


# 创建默认logger
default_logger = setup_logger(
    "StoryMaker",
    f"story_maker_{datetime.now().strftime('%Y%m%d')}.log"
)

