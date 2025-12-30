"""
玩家模式日志过滤器

负责：
- 拦截所有 Agent 日志
- 终端仅显示 GAME 级别日志
- 完整日志写入文件
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


# 定义自定义日志级别 GAME（介于 INFO(20) 和 WARNING(30) 之间）
GAME_LEVEL = 25
logging.addLevelName(GAME_LEVEL, "GAME")


def game(self, message, *args, **kwargs):
    """自定义 logger.game() 方法"""
    if self.isEnabledFor(GAME_LEVEL):
        self._log(GAME_LEVEL, message, args, **kwargs)


# 给 Logger 类添加 game 方法
logging.Logger.game = game


class PlayerLogFilter:
    """玩家模式日志过滤器"""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        初始化日志过滤器
        
        Args:
            log_dir: 日志目录路径，默认为 logs/
        """
        if log_dir is None:
            log_dir = Path("logs")
        
        # 确保 logs/ 目录存在
        log_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_dir = log_dir
        self.log_file = log_dir / f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # 文件处理器（记录所有级别）
        self.file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        self.file_handler.setLevel(logging.DEBUG)
        self.file_handler.setFormatter(
            logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
        )
        
        # 终端处理器（仅 GAME 级别）
        self.terminal_handler = logging.StreamHandler()
        self.terminal_handler.setLevel(GAME_LEVEL)
        self.terminal_handler.addFilter(self._game_level_filter)
        self.terminal_handler.setFormatter(
            logging.Formatter('%(message)s')
        )
    
    def _game_level_filter(self, record: logging.LogRecord) -> bool:
        """终端只显示 GAME 级别"""
        return record.levelno == GAME_LEVEL
    
    def setup_root_logger(self) -> None:
        """配置根日志器"""
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        
        # 移除现有的处理器
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        
        # 添加文件处理器（记录所有）
        root.addHandler(self.file_handler)
        
        # 添加终端处理器（仅 GAME 级别）
        root.addHandler(self.terminal_handler)
    
    def get_log_file_path(self) -> Path:
        """获取日志文件路径"""
        return self.log_file


def setup_player_logging(log_dir: Optional[Path] = None) -> PlayerLogFilter:
    """
    设置玩家模式日志
    
    Args:
        log_dir: 日志目录路径
    
    Returns:
        配置好的日志过滤器实例
    """
    filter_instance = PlayerLogFilter(log_dir)
    filter_instance.setup_root_logger()
    return filter_instance

