"""
NPC初始化模块
负责初始化NPC管理器和所有NPC Agent
"""
from typing import Dict, Any, List
from agents.online.layer3.npc_agent import NPCAgent, NPCManager
from utils.logger import setup_logger

logger = setup_logger("InitNPC")


def initialize_single_npc(character_data: Dict[str, Any]) -> NPCAgent:
    """
    初始化单个NPC
    
    Args:
        character_data: 角色数据
    
    Returns:
        NPCAgent实例
    """
    logger.info(f"🎭 初始化单个NPC: {character_data.get('name', '未知')}")
    
    try:
        npc = NPCAgent(character_data)
        logger.info(f"✅ NPC初始化完成: {npc.character_name}")
        return npc
    except Exception as e:
        logger.error(f"❌ NPC初始化失败: {e}")
        raise


def initialize_npc_manager(genesis_data: Dict[str, Any]) -> NPCManager:
    """
    初始化NPC管理器（自动批量创建所有NPC）
    
    Args:
        genesis_data: Genesis数据
    
    Returns:
        NPCManager实例
    """
    logger.info("🎭 开始初始化NPC管理器...")
    
    try:
        npc_manager = NPCManager(genesis_data)
        logger.info("✅ NPC管理器初始化完成")
        logger.info(f"   - 创建NPC数量: {len(npc_manager.npcs)}")
        return npc_manager
    except Exception as e:
        logger.error(f"❌ NPC管理器初始化失败: {e}")
        raise


def initialize_npc_list(characters_data: List[Dict[str, Any]]) -> Dict[str, NPCAgent]:
    """
    批量初始化多个NPC（手动方式）
    
    Args:
        characters_data: 角色数据列表
    
    Returns:
        {npc_id: NPCAgent} 字典
    """
    logger.info(f"🎭 开始批量初始化{len(characters_data)}个NPC...")
    
    npcs = {}
    failed_count = 0
    
    for char_data in characters_data:
        char_id = char_data.get("id")
        if not char_id:
            logger.warning("⚠️  跳过没有ID的角色")
            failed_count += 1
            continue
        
        try:
            npcs[char_id] = initialize_single_npc(char_data)
        except Exception as e:
            logger.warning(f"⚠️  NPC {char_id} 初始化失败: {e}")
            failed_count += 1
            continue
    
    logger.info(f"✅ 批量初始化完成")
    logger.info(f"   - 成功: {len(npcs)}个")
    logger.info(f"   - 失败: {failed_count}个")
    
    return npcs

