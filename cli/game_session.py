"""
游戏会话抽象基类

定义统一的游戏会话接口，确保 OS Agent 和 GameEngine 两种引擎
具有一致的行为。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass
class TurnResult:
    """回合结果（统一格式）"""
    success: bool
    text: str                               # 渲染后的输出文本
    error: Optional[str] = None
    scene_id: int = 0
    turn_id: int = 0
    npc_reactions: List[Dict] = field(default_factory=list)  # 标准化的 NPC 反应
    world_state_delta: Optional[Dict] = None


@dataclass
class SessionStatus:
    """会话状态（统一格式）"""
    scene_id: int
    turn_id: int
    location: str
    current_time: str
    present_characters: List[str]
    can_continue: bool


class GameSession(ABC):
    """游戏会话抽象基类（统一运行契约）"""
    
    @abstractmethod
    def start(self) -> str:
        """
        开始游戏，返回开场文本
        
        Returns:
            开场文本/描述
        """
        pass
    
    @abstractmethod
    def process_turn(self, player_input: str) -> TurnResult:
        """
        处理玩家输入，返回回合结果
        
        Args:
            player_input: 玩家输入的文本
        
        Returns:
            回合结果
        """
        pass
    
    @abstractmethod
    def save(self, save_name: str, at_boundary: bool = False) -> Path:
        """
        保存游戏，返回存档路径
        
        Args:
            save_name: 存档名称
            at_boundary: 是否在边界点（幕间/存档点），影响 can_switch_engine 状态
                        True = 安全点，允许切换引擎
                        False = 场景中途（如 /quit），禁止切换
        
        Returns:
            存档文件路径
        """
        pass
    
    @abstractmethod
    def get_status(self) -> SessionStatus:
        """
        获取当前会话状态
        
        Returns:
            会话状态
        """
        pass
    
    @abstractmethod
    def get_action_suggestions(self) -> List[str]:
        """
        获取行动建议
        
        Returns:
            行动建议列表（通常2个）
        """
        pass
    
    @abstractmethod
    def can_resume(self) -> bool:
        """
        是否可以断点续传
        
        契约：can_resume()==True 必须保证 resume() 可执行不抛异常
        
        Returns:
            True 如果可以恢复，False 否则
        """
        pass
    
    @abstractmethod
    def get_resume_error(self) -> Optional[str]:
        """
        获取无法恢复的原因
        
        注意：应在 can_resume()==False 后立即调用，避免中间状态变化
        实现建议：与 can_resume() 共享内部检查逻辑（如 _check_resume_state）
        
        Returns:
            None: 如果可以恢复
            str: 错误原因（如"progress.json 不存在"或"progress.json 已损坏"）
        """
        pass
    
    @abstractmethod
    def invalidate_resume_cache(self) -> None:
        """
        使恢复状态缓存失效
        
        调用时机：
        - progress.json 被外部修改后（如用户手动修复）
        - 返回菜单重新检查前
        - save() 内部会自动调用
        """
        pass
    
    @abstractmethod
    def resume(self) -> str:
        """
        从断点恢复，返回恢复提示
        
        前置条件：can_resume() 返回 True
        
        Returns:
            恢复提示字符串
        
        Raises:
            RuntimeError: 如果 progress.json 不存在或损坏
        """
        pass

