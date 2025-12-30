"""
会话工厂

根据配置选择并创建合适的游戏会话适配器。
"""

from pathlib import Path
from typing import Optional

from cli.game_session import GameSession
from cli.osagent_session import OSAgentSession
from cli.gameengine_session import GameEngineSession
from config.cli_config import DevConfig
from utils.logger import setup_logger

logger = setup_logger("SessionFactory", "session_factory.log")


class SessionFactory:
    """会话工厂（根据配置选择引擎）"""
    
    @staticmethod
    def create(
        runtime_dir: Path,
        world_dir: Path,
        engine_type: str = "osagent",
        config: Optional[DevConfig] = None
    ) -> GameSession:
        """
        创建游戏会话
        
        Args:
            runtime_dir: 运行时目录路径
            world_dir: 世界数据目录路径
            engine_type: 引擎类型 ("osagent" 或 "gameengine")
            config: 开发者配置，可选
        
        Returns:
            游戏会话实例
        
        Raises:
            ValueError: 如果引擎类型未知
        """
        logger.info(f"创建会话: engine={engine_type}, runtime={runtime_dir}")
        
        if engine_type == "osagent":
            return OSAgentSession(runtime_dir, world_dir)
        elif engine_type == "gameengine":
            genesis_path = runtime_dir / "genesis.json"
            return GameEngineSession(genesis_path, config)
        else:
            raise ValueError(f"未知引擎类型: {engine_type}")
    
    @staticmethod
    def get_engine_type_from_progress(runtime_dir: Path) -> Optional[str]:
        """
        从 progress.json 获取引擎类型
        
        Args:
            runtime_dir: 运行时目录路径
        
        Returns:
            引擎类型，如果无法读取返回 None
        """
        from utils.progress_tracker import ProgressTracker
        
        progress_file = runtime_dir / "plot" / "progress.json"
        if not progress_file.exists():
            return None
        
        progress = ProgressTracker().load_progress(runtime_dir)
        if progress.is_corrupted:
            return None
        
        return progress.engine_type

