"""
数据库初始化模块
负责初始化StateManager和相关存储组件
"""
from typing import Dict, Any
from uuid import uuid4
from utils.database import StateManager
from utils.logger import setup_logger

logger = setup_logger("InitDatabase")


def initialize_database(
    game_id: str = None,
    game_name: str = "未知世界",
    genesis_path: str = None
) -> StateManager:
    """
    初始化数据库状态管理器
    
    Args:
        game_id: 游戏ID，默认自动生成
        game_name: 游戏名称
        genesis_path: Genesis文件路径
    
    Returns:
        StateManager实例
    """
    logger.info("💾 开始初始化数据库状态管理器...")
    
    if game_id is None:
        game_id = uuid4().hex
        logger.info(f"   - 自动生成game_id: {game_id}")
    
    try:
        state_manager = StateManager(
            game_id=game_id,
            game_name=game_name,
            genesis_path=genesis_path or ""
        )
        logger.info("✅ 数据库状态管理器初始化完成")
        logger.info(f"   - 游戏ID: {game_id}")
        logger.info(f"   - 游戏名称: {game_name}")
        return state_manager
    except Exception as e:
        logger.error(f"❌ 数据库状态管理器初始化失败: {e}")
        raise


def initialize_character_cards_to_database(
    state_manager: StateManager,
    genesis_data: Dict[str, Any]
) -> int:
    """
    将Genesis中的角色卡导入数据库
    
    Args:
        state_manager: 状态管理器实例
        genesis_data: Genesis数据
    
    Returns:
        成功导入的角色卡数量
    """
    logger.info("📇 开始导入角色卡到数据库...")
    
    characters = genesis_data.get("characters", [])
    success_count = 0
    
    for char in characters:
        char_id = char.get("id")
        if not char_id:
            logger.warning("⚠️  跳过没有ID的角色")
            continue
        
        try:
            state_manager.record_character_card(
                character_id=char_id,
                version=1,
                card_data=char,
                changes=None,
                changed_by="genesis_import"
            )
            success_count += 1
        except Exception as e:
            logger.warning(f"⚠️  角色卡 {char_id} 导入失败: {e}")
            continue
    
    logger.info(f"✅ 角色卡导入完成: {success_count}/{len(characters)}")
    return success_count

