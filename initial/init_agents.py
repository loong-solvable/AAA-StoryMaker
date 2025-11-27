"""
Agent初始化模块
负责初始化各种核心Agent（Logic、Plot、Vibe等）
"""
from typing import Dict, Any, Tuple
from agents.online.layer1.logic_agent import LogicValidator
from agents.online.layer2.plot_agent import PlotDirector
from agents.online.layer2.vibe_agent import AtmosphereCreator
from utils.logger import setup_logger

logger = setup_logger("InitAgents")


def initialize_logic_agent(world_data: Dict[str, Any]) -> LogicValidator:
    """
    初始化逻辑审查官Agent
    
    Args:
        world_data: 世界设定数据（从Genesis提取）
    
    Returns:
        LogicValidator实例
    """
    logger.info("⚖️ 开始初始化逻辑审查官...")
    
    try:
        logic = LogicValidator()
        logic.set_world_rules(world_data)
        logger.info("✅ 逻辑审查官初始化完成")
        return logic
    except Exception as e:
        logger.error(f"❌ 逻辑审查官初始化失败: {e}")
        raise


def initialize_plot_agent(genesis_data: Dict[str, Any]) -> PlotDirector:
    """
    初始化剧情导演Agent
    
    Args:
        genesis_data: Genesis数据
    
    Returns:
        PlotDirector实例
    """
    logger.info("🎬 开始初始化剧情导演...")
    
    try:
        plot = PlotDirector(genesis_data)
        logger.info("✅ 剧情导演初始化完成")
        return plot
    except Exception as e:
        logger.error(f"❌ 剧情导演初始化失败: {e}")
        raise


def initialize_vibe_agent(genesis_data: Dict[str, Any]) -> AtmosphereCreator:
    """
    初始化氛围创造者Agent
    
    Args:
        genesis_data: Genesis数据
    
    Returns:
        AtmosphereCreator实例
    """
    logger.info("🎨 开始初始化氛围创造者...")
    
    try:
        vibe = AtmosphereCreator(genesis_data)
        logger.info("✅ 氛围创造者初始化完成")
        return vibe
    except Exception as e:
        logger.error(f"❌ 氛围创造者初始化失败: {e}")
        raise


def initialize_agents(genesis_data: Dict[str, Any]) -> Tuple[LogicValidator, PlotDirector, AtmosphereCreator]:
    """
    批量初始化所有核心Agent
    
    Args:
        genesis_data: Genesis数据
    
    Returns:
        (LogicValidator, PlotDirector, AtmosphereCreator) 元组
    """
    logger.info("🎯 开始批量初始化核心Agent...")
    
    world_data = genesis_data.get("world", {})
    
    logic = initialize_logic_agent(world_data)
    plot = initialize_plot_agent(genesis_data)
    vibe = initialize_vibe_agent(genesis_data)
    
    logger.info("✅ 所有核心Agent初始化完成")
    
    return logic, plot, vibe

