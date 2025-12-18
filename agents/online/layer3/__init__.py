# 第三层：演员组（表现层）
from .npc_agent import NPCAgent, NPCManager
from .screen_agent import ScreenAgent, ScreenInput, create_screen_agent

__all__ = ["NPCAgent", "NPCManager", "ScreenAgent", "ScreenInput", "create_screen_agent"]
