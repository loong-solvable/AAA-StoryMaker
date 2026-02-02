"""
CLI 配置模块
定义玩家入口和开发者入口的配置参数

注意：从 v0.4.0 开始，默认引擎类型改为 'gameengine'
GameEngine 包含完整的 Conductor 幕管理系统，支持：
- 三模式分流（DIALOGUE/PLOT_ADVANCE/ACT_TRANSITION）
- 紧迫度驱动的幕转换
- NPC 幕级指令
- 异步并行优化
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
    # 默认使用 GameEngine（包含 Conductor 幕管理系统）
    ENGINE_TYPE: str = "gameengine"


@dataclass
class DevConfig:
    """开发者入口配置"""
    SHOW_LOGS: bool = True
    SHOW_AGENT_STATUS: bool = True
    SHOW_PERFORMANCE: bool = True
    ENABLE_VIBE: bool = True
    ENABLE_SCREEN_AGENT: bool = True
    DEFAULT_MAX_TURNS: int = 50
    LOG_LEVEL: str = "DEBUG"
    # 默认使用 GameEngine（包含 Conductor 幕管理系统）
    ENGINE_TYPE: str = "gameengine"
    DEFAULT_CONCURRENCY: int = 5
    ENABLE_PARALLEL: bool = True
    
    # GameEngine 引擎的场景映射配置
    # 每 N 轮对话视为一个场景（用于 scene_id 计算）
    TURNS_PER_SCENE: int = 10

