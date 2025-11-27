"""
初始化模块
集中管理所有初始化功能
"""

from .init_llm import initialize_llm
from .init_genesis import load_genesis_data  # 兼容旧格式
from .init_world import load_world_data, load_world_setting, load_characters_list  # 新格式
from .init_world_state import initialize_world_state
from .init_agents import initialize_agents
from .init_npc import initialize_npc_manager
from .init_database import initialize_database

__all__ = [
    "initialize_llm",
    "load_genesis_data",  # 旧格式
    "load_world_data",    # 新格式
    "load_world_setting",
    "load_characters_list",
    "initialize_world_state",
    "initialize_agents",
    "initialize_npc_manager",
    "initialize_database",
]

