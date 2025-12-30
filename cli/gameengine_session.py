"""
GameEngine 会话适配器

将 GameEngine 封装为统一的 GameSession 接口。
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from cli.game_session import GameSession, TurnResult, SessionStatus
from config.cli_config import DevConfig
from utils.progress_tracker import ProgressTracker, ProgressData, DEFAULT_CAN_SWITCH
from utils.logger import setup_logger

logger = setup_logger("GameEngineSession", "gameengine_session.log")


class GameEngineSession(GameSession):
    """GameEngine 的会话适配器"""
    
    def __init__(self, genesis_path: Path, config: Optional[DevConfig] = None):
        """
        初始化 GameEngine 会话
        
        Args:
            genesis_path: genesis.json 文件路径
            config: 开发者配置，可选
        """
        self.genesis_path = genesis_path
        self.runtime_dir = genesis_path.parent
        self.config = config or DevConfig()
        self.engine = None
        self.progress_tracker = ProgressTracker()
        self._scene_id = 1       # 内部维护的 scene_id
        self._next_scene_id = 2  # 下一场景 ID
        self._turn_count = 0     # 累计回合数
    
    def start(self) -> str:
        """开始游戏"""
        from game_engine import GameEngine
        
        self.engine = GameEngine(self.genesis_path)
        
        # 从 progress.json 恢复 scene_id 和 turn_count
        progress = self.progress_tracker.load_progress(self.runtime_dir)
        self._scene_id = progress.current_scene_id
        self._turn_count = progress.turn_count
        
        # GameEngine 采用线性策略：无论 progress 中 next_scene_id 是什么，
        # 都重置为 current + 1，确保与 process_turn 的线性推进一致
        # 
        # ⚠️ 已知限制：OS Agent 的非线性场景路径在切换到 GameEngine 后会丢失
        # 例如 OS→GE→OS 切换时，原本的分支信息无法恢复
        # 这是 GameEngine 不支持非线性场景的固有限制，非 bug
        self._next_scene_id = self._scene_id + 1
        
        logger.info(f"GameEngine 启动: scene={self._scene_id}, turn={self._turn_count}")
        
        return self.engine.start_game()
    
    def process_turn(self, player_input: str) -> TurnResult:
        """处理一个回合"""
        # 回合开始时立即持久化，禁止切换引擎（防止重启后允许不安全切换）
        self.progress_tracker.save_progress(
            runtime_dir=self.runtime_dir,
            current_scene_id=self._scene_id,
            next_scene_id=self._next_scene_id,
            turn_count=self._turn_count,
            engine_type="gameengine",
            can_switch_engine=False  # 回合中禁止切换
        )
        self.invalidate_resume_cache()  # 每次写入后失效缓存
        
        try:
            result = self.engine.process_turn(player_input)
            
            # 从 GameEngine 获取回合数
            self._turn_count = getattr(self.engine, 'turn_count', self._turn_count + 1)
            current_turn = self._turn_count
            
            # scene_id 映射策略（可配置，默认 10 轮/场景）
            turns_per_scene = getattr(self.config, 'TURNS_PER_SCENE', 10)
            computed_scene_id = (current_turn - 1) // turns_per_scene + 1
            
            # 场景切换时更新 scene_id 和 next_scene_id
            # 注意：GameEngine 采用线性推进策略（_next_scene_id = _scene_id + 1）
            # 这与 OS Agent 的非线性场景策略不同，但保证 progress.json 语义一致
            # （current_scene_id < next_scene_id 恒成立）
            if computed_scene_id > self._scene_id:
                self._scene_id = computed_scene_id
                self._next_scene_id = self._scene_id + 1  # 线性推进，保证语义正确
            
            # 回合结束后再次持久化（防止处理成功但进程异常退出导致进度丢失）
            self.progress_tracker.save_progress(
                runtime_dir=self.runtime_dir,
                current_scene_id=self._scene_id,
                next_scene_id=self._next_scene_id,
                turn_count=self._turn_count,  # 更新后的回合数
                engine_type="gameengine",
                can_switch_engine=False  # 仍处于回合间，非边界点
            )
            
            # 进度已更新，使缓存失效（确保后续 can_resume 反映最新状态）
            self.invalidate_resume_cache()
            
            return TurnResult(
                success=result.get("success", True),
                text=result.get("text", ""),
                error=result.get("error"),
                scene_id=self._scene_id,
                turn_id=current_turn,
                npc_reactions=result.get("npc_reactions", [])
            )
            
        except Exception as e:
            logger.error(f"GameEngine 处理回合失败: {e}", exc_info=True)
            return TurnResult(
                success=False,
                text="",
                error=str(e),
                scene_id=self._scene_id,
                turn_id=self._turn_count
            )
    
    def save(self, save_name: str, at_boundary: bool = False) -> Path:
        """
        保存游戏进度
        
        Args:
            save_name: 存档名称
            at_boundary: 是否在边界点（如关卡完成、存档点）
        """
        # 1. 保存 GameEngine 原生存档
        if self.engine and hasattr(self.engine, 'save_game'):
            self.engine.save_game(save_name)
        
        # 2. 同步更新 progress.json（统一断点来源）
        self.progress_tracker.save_progress(
            runtime_dir=self.runtime_dir,
            current_scene_id=self._scene_id,
            next_scene_id=self._next_scene_id,
            turn_count=self._turn_count,
            engine_type="gameengine",
            can_switch_engine=at_boundary  # 仅边界时允许切换
        )
        
        # 保存后使缓存失效，允许后续重新检测
        self.invalidate_resume_cache()
        
        logger.info(f"GameEngine 保存: {save_name}, at_boundary={at_boundary}")
        
        # 返回进度文件路径（统一入口）
        return self.runtime_dir / "plot" / "progress.json"
    
    def get_status(self) -> SessionStatus:
        """获取当前会话状态"""
        # 从 GameEngine 获取状态
        location = ""
        current_time = ""
        present_characters = []
        
        if self.engine:
            context = getattr(self.engine, 'os', None)
            if context:
                world_context = getattr(context, 'world_context', None)
                if world_context:
                    location = getattr(world_context, 'current_location', "")
                    current_time = getattr(world_context, 'current_time', "")
                    present_characters = getattr(world_context, 'present_characters', [])
        
        return SessionStatus(
            scene_id=self._scene_id,
            turn_id=self._turn_count,
            location=location,
            current_time=current_time,
            present_characters=present_characters,
            can_continue=True
        )
    
    def get_action_suggestions(self) -> List[str]:
        """获取行动建议"""
        if self.engine and hasattr(self.engine, 'get_available_actions'):
            return self.engine.get_available_actions()
        return []
    
    def _check_resume_state(self) -> Tuple[bool, Optional[str]]:
        """
        内部方法：检查恢复状态（带缓存，避免 load_progress 副作用）
        
        重要：load_progress() 在检测到损坏时会重命名文件，
        因此必须缓存首次检查结果，后续调用直接返回缓存。
        """
        if hasattr(self, '_resume_state_cache'):
            return self._resume_state_cache
        
        progress_file = self.runtime_dir / "plot" / "progress.json"
        if not progress_file.exists():
            self._resume_state_cache = (False, "progress.json 不存在")
            return self._resume_state_cache
        
        progress = self.progress_tracker.load_progress(self.runtime_dir)
        if progress.is_corrupted:
            self._resume_state_cache = (False, "progress.json 已损坏，请手动修复备份文件")
            return self._resume_state_cache
        
        self._resume_state_cache = (True, None)
        return self._resume_state_cache
    
    def invalidate_resume_cache(self) -> None:
        """使缓存失效（如 progress.json 被外部修改后调用）"""
        if hasattr(self, '_resume_state_cache'):
            delattr(self, '_resume_state_cache')
    
    def can_resume(self) -> bool:
        """
        检查是否可以断点续传
        
        契约：can_resume()==True 必须保证 resume() 可执行不抛异常
        
        重要：
        - 仅检查 progress.json，不检查 saves/ 目录
        - 同时检查文件存在性和完整性（is_corrupted）
        """
        can_resume, _ = self._check_resume_state()
        return can_resume
    
    def get_resume_error(self) -> Optional[str]:
        """
        获取无法恢复的原因
        
        注意：结果已缓存，与 can_resume() 保持一致
        """
        _, error = self._check_resume_state()
        return error
    
    def resume(self) -> str:
        """
        从断点恢复（语义等同于 start() 但走恢复路径）
        
        行为规范：
        1. 检查 progress.json 存在性和完整性
        2. 加载 progress.json 恢复 scene_id 和 turn_count
        3. 初始化 GameEngine（跳过新游戏开场）
        4. 返回恢复提示文本
        
        前置条件：can_resume() 返回 True
        返回值：统一格式的恢复提示字符串
        
        Raises:
            RuntimeError: 如果 progress.json 不存在或损坏
        """
        from game_engine import GameEngine
        
        # 前置检查：使用缓存的结果（存在性+完整性）
        if not self.can_resume():
            # 使用 get_resume_error() 获取具体原因（与 B-07a 契约一致）
            error = self.get_resume_error() or "未知原因"
            raise RuntimeError(f"无法恢复：{error}")
        
        # 此时 can_resume()=True，可以安全加载
        progress = self.progress_tracker.load_progress(self.runtime_dir)
        
        self.engine = GameEngine(self.genesis_path)
        
        # 从 progress 恢复状态
        self._scene_id = progress.current_scene_id
        self._next_scene_id = progress.next_scene_id
        self._turn_count = progress.turn_count
        
        # 恢复 GameEngine 内部状态（如果支持）
        if hasattr(self.engine, 'restore_from_turn'):
            self.engine.restore_from_turn(self._turn_count)
        
        logger.info(f"GameEngine 恢复: scene={self._scene_id}, turn={self._turn_count}")
        
        return (
            f"📂 已从断点恢复\n"
            f"   场景: 第 {self._scene_id} 幕\n"
            f"   累计回合: {self._turn_count}\n"
            f"   继续你的冒险..."
        )

