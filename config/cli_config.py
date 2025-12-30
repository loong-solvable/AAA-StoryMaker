"""
CLI 配置模块
定义玩家入口和开发者入口的配置参数
"""

from dataclasses import dataclass


@dataclass
class PlayerConfig:
    """玩家入口配置"""
    SHOW_LOGS: bool = False
    SHOW_AGENT_STATUS: bool = False
    SHOW_PERFORMANCE: bool = False
    ENABLE_VIBE: bool = True
    ENABLE_SCREEN_AGENT: bool = True
    DEFAULT_MAX_TURNS: int = 15
    LOG_LEVEL: str = "WARNING"
    ENGINE_TYPE: str = "osagent"


@dataclass
class DevConfig:
    """开发者入口配置"""
    SHOW_LOGS: bool = True
    SHOW_AGENT_STATUS: bool = True
    SHOW_PERFORMANCE: bool = True
    ENABLE_VIBE: bool = True
    ENABLE_SCREEN_AGENT: bool = True  # 仅 OS Agent 支持，见兼容性说明
    DEFAULT_MAX_TURNS: int = 50
    LOG_LEVEL: str = "DEBUG"
    ENGINE_TYPE: str = "osagent"
    DEFAULT_CONCURRENCY: int = 5
    ENABLE_PARALLEL: bool = True
    
    # GameEngine 引擎的场景映射配置
    # 每 N 轮对话视为一个场景（用于 scene_id 计算）
    # 此值应与 OS Agent 的平均场景长度保持一致
    TURNS_PER_SCENE: int = 10

