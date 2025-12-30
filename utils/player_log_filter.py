"""
玩家模式日志过滤器

负责：
- 拦截所有 Agent 日志（OS, Plot, WS, Vibe, NPC 等）
- 终端仅显示 GAME 级别日志和严重错误
- 完整日志写入文件供调试
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Set


# 定义自定义日志级别 GAME（介于 INFO(20) 和 WARNING(30) 之间）
GAME_LEVEL = 25
logging.addLevelName(GAME_LEVEL, "GAME")


def game(self, message, *args, **kwargs):
    """自定义 logger.game() 方法"""
    if self.isEnabledFor(GAME_LEVEL):
        self._log(GAME_LEVEL, message, args, **kwargs)


# 给 Logger 类添加 game 方法
logging.Logger.game = game


# 需要完全静默的模块名（这些模块的日志绝不会出现在终端）
SILENCED_MODULES: Set[str] = {
    # Layer 1
    "OS", "Logic", "Conductor",
    # Layer 2
    "Plot", "WS", "Vibe", "WorldState",
    # Layer 3
    "NPCManager", "NPC", "SceneNarrator",
    # 工具类
    "LLMFactory", "JSONParser", "FileUtils", "MemoryManager",
    "ProgressTracker", "SceneMemory", "AllSceneMemory",
    "WorldStateSync", "InActAccumulator",
    # 初始化
    "IlluminatiInit", "WorldBuilder", "GenesisGroup",
    # 会话管理
    "SessionFactory", "OSAgentSession", "GameEngineSession",
    "WorldManager", "EngineResolver", "PlayerProfile",
}


class SilentFilter(logging.Filter):
    """
    静默过滤器 - 阻止所有 Agent 日志输出到终端
    仅允许 GAME 级别 或 CRITICAL 级别通过
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        # 允许 GAME 级别通过（用于玩家可见的信息）
        if record.levelno == GAME_LEVEL:
            return True
        
        # 允许 CRITICAL 级别通过（严重错误玩家需要知道）
        if record.levelno >= logging.CRITICAL:
            return True
        
        # 检查是否是被静默的模块
        logger_name = record.name
        for silenced in SILENCED_MODULES:
            if silenced in logger_name:
                return False
        
        # 默认阻止所有其他日志
        return False


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
        
        # 文件处理器（记录所有级别，用于调试）
        self.file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        self.file_handler.setLevel(logging.DEBUG)
        self.file_handler.setFormatter(
            logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
        )
        
        # 终端处理器（应用静默过滤器）
        self.terminal_handler = logging.StreamHandler(sys.stdout)
        self.terminal_handler.setLevel(logging.DEBUG)  # 让过滤器决定
        self.terminal_handler.addFilter(SilentFilter())
        self.terminal_handler.setFormatter(
            logging.Formatter('%(message)s')  # 简洁格式
        )
    
    def setup_root_logger(self) -> None:
        """配置根日志器"""
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        
        # 移除现有的处理器
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        
        # 添加文件处理器（记录所有，供调试）
        root.addHandler(self.file_handler)
        
        # 添加终端处理器（静默模式）
        root.addHandler(self.terminal_handler)
        
        # 额外：静默第三方库的日志
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("langchain").setLevel(logging.WARNING)
    
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

