"""
世界状态初始化模块
负责初始化世界上下文和世界状态管理器
"""
from typing import Dict, Any
from agents.message_protocol import WorldContext
from agents.online.layer2.ws_agent import WorldStateManager
from utils.logger import setup_logger

logger = setup_logger("InitWorldState")


def initialize_world_context(genesis_data: Dict[str, Any]) -> WorldContext:
    """
    初始化世界上下文
    
    Args:
        genesis_data: Genesis数据
    
    Returns:
        WorldContext实例
    """
    logger.info("🌍 开始初始化世界上下文...")
    
    world_start = genesis_data.get("world_start_context", {})
    
    world_context = WorldContext(
        current_time=world_start.get("suggested_time", "下午"),
        current_location=world_start.get("suggested_location", "loc_001"),
        present_characters=world_start.get("key_characters", []),
        recent_events=[],
        world_state={
            "turn": 0,
            "game_started": False
        }
    )
    
    logger.info("✅ 世界上下文初始化完成")
    logger.info(f"   - 初始时间: {world_context.current_time}")
    logger.info(f"   - 初始位置: {world_context.current_location}")
    logger.info(f"   - 在场角色: {len(world_context.present_characters)}个")
    
    return world_context


def initialize_world_state(genesis_data: Dict[str, Any]) -> WorldStateManager:
    """
    初始化世界状态管理器
    
    Args:
        genesis_data: Genesis数据
    
    Returns:
        WorldStateManager实例
    """
    logger.info("🌍 开始初始化世界状态管理器...")
    
    try:
        world_state_manager = WorldStateManager(genesis_data)
        logger.info("✅ 世界状态管理器初始化完成")
        return world_state_manager
    except Exception as e:
        logger.error(f"❌ 世界状态管理器初始化失败: {e}")
        raise

