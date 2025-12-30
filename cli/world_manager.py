"""
世界管理模块

负责：
- 列出可用世界
- 获取世界详细信息
- 列出运行时目录
- 获取运行时详细信息
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any

from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger("WorldManager", "world_manager.log")


@dataclass
class WorldInfo:
    """世界信息"""
    name: str
    title: str = ""
    genre: str = ""
    description: str = ""
    character_count: int = 0
    world_dir: Path = None
    
    def __post_init__(self):
        if self.world_dir is None:
            self.world_dir = settings.DATA_DIR / "worlds" / self.name


@dataclass
class RuntimeInfo:
    """运行时信息"""
    path: Path
    name: str
    world_name: str = ""
    initialized_at: str = ""
    llm_model: str = ""
    current_scene_id: int = 1
    turn_count: int = 0
    engine_type: str = "osagent"


class WorldManager:
    """世界管理器"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        初始化世界管理器
        
        Args:
            data_dir: 数据目录路径，默认使用 settings.DATA_DIR
        """
        self.data_dir = data_dir or settings.DATA_DIR
        self.worlds_dir = self.data_dir / "worlds"
        self.runtime_dir = self.data_dir / "runtime"
    
    def list_available_worlds(self) -> List[WorldInfo]:
        """
        获取所有可用的世界
        
        Returns:
            世界信息列表
        """
        if not self.worlds_dir.exists():
            return []
        
        worlds = []
        for world_dir in self.worlds_dir.iterdir():
            if world_dir.is_dir() and (world_dir / "world_setting.json").exists():
                info = self.get_world_info(world_dir.name)
                if info:
                    worlds.append(info)
        
        return sorted(worlds, key=lambda w: w.name)
    
    def get_world_info(self, world_name: str) -> Optional[WorldInfo]:
        """
        获取世界的详细信息
        
        Args:
            world_name: 世界名称
        
        Returns:
            世界信息，如果不存在返回 None
        """
        world_dir = self.worlds_dir / world_name
        if not world_dir.exists():
            return None
        
        info = WorldInfo(name=world_name, world_dir=world_dir)
        
        # 读取世界设定
        setting_file = world_dir / "world_setting.json"
        if setting_file.exists():
            try:
                with open(setting_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    meta = data.get("meta", {})
                    info.title = meta.get("world_name", world_name)
                    info.genre = meta.get("genre_type", "未知")
                    info.description = meta.get("description", "")[:100]
            except Exception as e:
                logger.warning(f"读取世界设定失败 {world_name}: {e}")
        
        # 读取角色列表
        chars_file = world_dir / "characters_list.json"
        if chars_file.exists():
            try:
                with open(chars_file, "r", encoding="utf-8") as f:
                    chars = json.load(f)
                    info.character_count = len(chars)
            except Exception as e:
                logger.warning(f"读取角色列表失败 {world_name}: {e}")
        
        return info
    
    def list_runtimes(self, world_name: str) -> List[RuntimeInfo]:
        """
        获取指定世界的运行时目录列表
        
        Args:
            world_name: 世界名称
        
        Returns:
            运行时信息列表（按修改时间降序排列）
        """
        if not self.runtime_dir.exists():
            return []
        
        runtimes = []
        for rt_dir in self.runtime_dir.iterdir():
            if rt_dir.is_dir() and rt_dir.name.startswith(f"{world_name}_"):
                info = self.get_runtime_info(rt_dir)
                if info:
                    runtimes.append(info)
        
        return sorted(runtimes, key=lambda r: r.initialized_at, reverse=True)
    
    def get_runtime_info(self, runtime_dir: Path) -> Optional[RuntimeInfo]:
        """
        获取运行时目录的详细信息
        
        Args:
            runtime_dir: 运行时目录路径
        
        Returns:
            运行时信息，如果无效返回 None
        """
        if not runtime_dir.is_dir():
            return None
        
        # 检查是否是有效的运行时目录
        summary_file = runtime_dir / "init_summary.json"
        if not summary_file.exists():
            return None
        
        info = RuntimeInfo(
            path=runtime_dir,
            name=runtime_dir.name,
        )
        
        # 从目录名提取世界名称
        parts = runtime_dir.name.split("_")
        if len(parts) >= 1:
            info.world_name = parts[0]
        
        # 读取初始化摘要
        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                summary = json.load(f)
                info.initialized_at = summary.get("initialized_at", "未知")
                info.llm_model = summary.get("llm_config", {}).get("model", "未知")
        except Exception as e:
            logger.warning(f"读取 init_summary.json 失败: {e}")
        
        # 读取进度信息
        progress_file = runtime_dir / "plot" / "progress.json"
        if progress_file.exists():
            try:
                with open(progress_file, "r", encoding="utf-8") as f:
                    progress = json.load(f)
                    info.current_scene_id = progress.get("current_scene_id", 1)
                    info.turn_count = progress.get("turn_count", 0)
                    info.engine_type = progress.get("engine_type", "osagent")
            except Exception as e:
                logger.warning(f"读取 progress.json 失败: {e}")
        
        return info
    
    def get_world_dir(self, world_name: str) -> Path:
        """获取世界目录路径"""
        return self.worlds_dir / world_name
    
    def world_exists(self, world_name: str) -> bool:
        """检查世界是否存在"""
        world_dir = self.worlds_dir / world_name
        return world_dir.exists() and (world_dir / "world_setting.json").exists()


# 全局单例
world_manager = WorldManager()

