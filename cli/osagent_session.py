"""
OS Agent 会话适配器

将 OS Agent 流程封装为统一的 GameSession 接口。

重要修复（v0.10.2）：
1. 添加 scene_memory 实例变量，用于幕间过渡
2. 修正 process_scene_transition 调用，传入 scene_memory
3. 修正游戏流程：先让 NPC 演一段（建立场景），然后才让玩家发言
4. max_turns 改为 15（与 main_old.py 一致）
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from cli.game_session import GameSession, TurnResult, SessionStatus
from utils.progress_tracker import ProgressTracker, ProgressData, DEFAULT_CAN_SWITCH
from utils.logger import setup_logger

logger = setup_logger("OSAgentSession", "osagent_session.log")


class OSAgentSession(GameSession):
    """OS Agent 流程的会话适配器"""
    
    def __init__(self, runtime_dir: Path, world_dir: Path):
        """
        初始化 OS Agent 会话
        
        Args:
            runtime_dir: 运行时目录路径
            world_dir: 世界数据目录路径
        """
        self.runtime_dir = runtime_dir
        self.world_dir = world_dir
        self.os_agent = None
        self.screen_agent = None
        self.progress_tracker = ProgressTracker()
        self.current_scene_id = 1
        self._next_scene_id = 2  # 支持非线性场景
        self._total_turn_count = 0  # 累计回合数（跨场景）
        self._last_rendered_text = ""
        self._scene_memory = None  # 场景记忆，用于幕间过渡
        self._pending_player_input = None  # 待处理的玩家输入
    
    def _init_agents(self, fail_on_corrupted: bool = False) -> None:
        """
        内部方法：初始化 Agent 实例和恢复进度
        
        注意：此方法不产生任何副作用（如生成开场剧本），
        仅创建 Agent 实例并加载进度数据。
        
        Args:
            fail_on_corrupted: 是否在 progress.json 损坏时抛错
                - True: resume() 调用时使用，fail-fast 防止数据丢失
                - False: start() 调用时使用，损坏时使用默认进度继续新游戏
        
        Raises:
            RuntimeError: 仅当 fail_on_corrupted=True 且 progress.json 损坏时
        """
        import importlib.util
        from agents.online.layer3.screen_agent import ScreenAgent
        
        # 初始化 OS Agent
        os_file = Path(__file__).parent.parent / "agents" / "online" / "layer1" / "os_agent.py"
        spec = importlib.util.spec_from_file_location("os_agent", os_file)
        os_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(os_module)
        
        genesis_path = self.runtime_dir / "genesis.json"
        if genesis_path.exists():
            self.os_agent = os_module.OperatingSystem(genesis_path)
        else:
            self.os_agent = os_module.OperatingSystem()
        
        # 初始化 Screen Agent
        world_name = self.world_dir.name if self.world_dir else ""
        self.screen_agent = ScreenAgent(runtime_dir=self.runtime_dir, world_name=world_name)
        
        # 加载完整进度（含 turn_count 和 next_scene_id）
        progress = self.progress_tracker.load_progress(self.runtime_dir)
        
        if progress.is_corrupted:
            if fail_on_corrupted:
                raise RuntimeError(
                    f"progress.json 已损坏，无法恢复游戏。\n"
                    f"请手动修复备份文件或删除运行时目录：{self.runtime_dir}"
                )
            # 新游戏：损坏时使用默认进度（符合 Q4 规范）
            progress = ProgressData()  # 使用默认值
        
        self.current_scene_id = progress.current_scene_id
        self._next_scene_id = progress.next_scene_id  # 恢复非线性场景信息
        self._total_turn_count = progress.turn_count
    
    def _create_scene_memory(self):
        """创建场景记忆板"""
        from utils.scene_memory import create_scene_memory
        self._scene_memory = create_scene_memory(self.runtime_dir, scene_id=self.current_scene_id)
        return self._scene_memory
    
    def start(self) -> str:
        """
        开始新游戏
        
        行为：
        1. 初始化 Agent
        2. 初始化 NPC 和剧本分发
        3. 运行初始场景循环，让 NPC 先建立场景（关键！）
        4. 返回场景渲染结果
        
        注意：即使 progress.json 损坏，也使用默认进度继续（符合 Q4 规范）
        """
        self._init_agents(fail_on_corrupted=False)  # 新游戏不 fail-fast
        
        # 初始化场景（NPC 初始化和剧本分发）
        self._initialize_scene()
        
        # 创建场景记忆
        self._create_scene_memory()
        
        # 运行初始场景循环：让 NPC 先演一段，建立场景
        # 关键：此时不传入玩家输入，只让 NPC 开场
        opening_text = self._run_initial_scene()
        
        logger.info(f"游戏开始: scene={self.current_scene_id}, world={self.world_dir.name}")
        
        return opening_text
    
    def _initialize_scene(self) -> None:
        """
        初始化场景：NPC 初始化 + 剧本分发
        """
        # 1. 确保 NPC 已初始化
        self.os_agent.ensure_scene_characters_initialized(
            runtime_dir=self.runtime_dir,
            world_dir=self.world_dir
        )
        
        # 2. 分发剧本给 NPC（关键！没有这步 NPC 就没有本幕目标）
        try:
            dispatch_result = self.os_agent.dispatch_script_to_actors(self.runtime_dir)
            if dispatch_result:
                logger.info(f"剧本分发完成: {len(dispatch_result)} 个 NPC 获得任务")
        except Exception as e:
            logger.warning(f"剧本分发失败: {e}")
    
    def _run_initial_scene(self) -> str:
        """
        运行初始场景循环：让 NPC 先建立场景
        
        流程：运行 run_scene_loop，但不提供玩家输入回调
        这样 NPC 会先开场，轮到玩家时循环会暂停
        
        Returns:
            场景渲染文本
        """
        # 定义一个"暂停"回调 - 轮到玩家时返回 None 表示暂停
        def pause_for_player(prompt: str) -> Optional[str]:
            # 返回 None 让循环暂停，等待真正的玩家输入
            return None
        
        try:
            # 运行场景循环，让 NPC 先演
            # max_turns 设置足够大，让 NPC 有机会建立场景
            # 但因为 pause_for_player 返回 None，实际会在轮到玩家时暂停
            loop_result = self.os_agent.run_scene_loop(
                runtime_dir=self.runtime_dir,
                world_dir=self.world_dir,
                max_turns=15,
                user_input_callback=pause_for_player,
                screen_callback=self._screen_callback
            )
            
            # 记录初始轮数
            turns = loop_result.get("total_turns", 0)
            self._total_turn_count = turns
            
            # 检查是否场景已结束（NPC 主动结束）
            is_scene_finished = loop_result.get("scene_finished", False)
            if is_scene_finished:
                self._handle_scene_transition()
            
        except Exception as e:
            logger.warning(f"初始场景循环异常: {e}")
        
        # 返回已渲染的内容
        return self._last_rendered_text or "[Scene started]"
    
    def process_turn(self, player_input: str) -> TurnResult:
        """
        处理一个回合：传入玩家输入，继续场景循环
        
        流程：
        1. 将玩家输入传给 run_scene_loop
        2. NPC 响应玩家输入
        3. 检测场景边界，处理幕间过渡
        """
        # 回合开始时立即持久化，禁止切换引擎
        self.progress_tracker.save_progress(
            runtime_dir=self.runtime_dir,
            current_scene_id=self.current_scene_id,
            next_scene_id=self._next_scene_id,
            turn_count=self._total_turn_count,
            engine_type="osagent",
            can_switch_engine=False
        )
        self.invalidate_resume_cache()
        
        try:
            # 确保 NPC 已初始化
            self.os_agent.ensure_scene_characters_initialized(
                runtime_dir=self.runtime_dir,
                world_dir=self.world_dir
            )
            
            # 确保场景记忆存在
            if self._scene_memory is None:
                self._create_scene_memory()
            
            # 使用玩家输入回调
            input_used = False
            def player_input_callback(prompt: str) -> Optional[str]:
                nonlocal input_used
                if not input_used:
                    input_used = True
                    return player_input
                # 第二次调用时暂停，等待下一次 process_turn
                return None
            
            # 继续场景循环
            loop_result = self.os_agent.run_scene_loop(
                runtime_dir=self.runtime_dir,
                world_dir=self.world_dir,
                max_turns=15,
                user_input_callback=player_input_callback,
                screen_callback=self._screen_callback
            )
            
            # 累加回合数
            turns_this_call = loop_result.get("total_turns", 1)
            self._total_turn_count += turns_this_call
            
            # 检测是否到达场景边界
            is_success = loop_result.get("success", False)
            is_scene_boundary = is_success and loop_result.get("scene_finished", False)
            
            # 如果场景结束，处理幕间过渡
            if is_scene_boundary:
                self._handle_scene_transition()
            
            # 回合结束后落盘
            self.progress_tracker.save_progress(
                runtime_dir=self.runtime_dir,
                current_scene_id=self.current_scene_id,
                next_scene_id=self._next_scene_id,
                turn_count=self._total_turn_count,
                engine_type="osagent",
                can_switch_engine=is_scene_boundary
            )
            self.invalidate_resume_cache()
            
            return TurnResult(
                success=is_success,
                text=self._last_rendered_text,
                scene_id=self.current_scene_id,
                turn_id=self._total_turn_count,
                npc_reactions=self._normalize_reactions(loop_result)
            )
            
        except Exception as e:
            logger.error(f"处理回合失败: {e}", exc_info=True)
            return TurnResult(
                success=False,
                text="",
                error=str(e),
                scene_id=self.current_scene_id,
                turn_id=self._total_turn_count
            )
    
    def _handle_scene_transition(self):
        """
        处理幕间过渡
        
        调用 process_scene_transition() 推进到下一幕
        注意：必须传入 scene_memory 参数
        """
        try:
            # 确保场景记忆存在
            if self._scene_memory is None:
                self._create_scene_memory()
            
            # 调用 OS Agent 的幕间处理（传入 scene_memory）
            if hasattr(self.os_agent, 'process_scene_transition'):
                transition_result = self.os_agent.process_scene_transition(
                    runtime_dir=self.runtime_dir,
                    world_dir=self.world_dir,
                    scene_memory=self._scene_memory,  # 关键修复！
                    scene_summary=f"第{self.current_scene_id}幕剧情演绎完成。"
                )
                
                if transition_result.get("success"):
                    # 更新场景 ID
                    self.current_scene_id = transition_result.get(
                        "next_scene_id", 
                        self.current_scene_id + 1
                    )
                    self._next_scene_id = transition_result.get(
                        "following_scene_id",
                        self.current_scene_id + 1
                    )
                    
                    # 创建新场景的记忆板
                    self._create_scene_memory()
                    
                    logger.info(f"幕间过渡完成: 进入第 {self.current_scene_id} 幕")
                else:
                    logger.warning(f"幕间过渡失败: {transition_result.get('error')}")
            else:
                # 简单推进
                self.current_scene_id += 1
                self._next_scene_id = self.current_scene_id + 1
                self._create_scene_memory()
                logger.info(f"简单幕间推进: 进入第 {self.current_scene_id} 幕")
                
        except Exception as e:
            logger.error(f"幕间过渡异常: {e}", exc_info=True)
            # 即使失败也推进场景，避免卡住
            self.current_scene_id += 1
            self._next_scene_id = self.current_scene_id + 1
            self._create_scene_memory()
    
    def _screen_callback(self, event: str, data: dict):
        """Screen Agent 渲染回调"""
        if event == "scene_start":
            self.screen_agent.render_scene_header(
                scene_id=data.get("scene_id", self.current_scene_id),
                location_name=data.get("location", ""),
                description=data.get("description", "")
            )
        elif event in {"dialogue", "player_input"}:
            self.screen_agent.render_single_dialogue(
                speaker=data.get("speaker", ""),
                content=data.get("content", ""),
                action=data.get("action", ""),
                emotion=data.get("emotion", ""),
                is_player=(event == "player_input"),
            )
            self._last_rendered_text = data.get("content", "")
        elif event == "scene_end":
            pass  # 可以添加场景结束渲染
    
    def _normalize_reactions(self, loop_result: dict) -> List[Dict]:
        """标准化 NPC 反应数据"""
        reactions = []
        for reaction in loop_result.get("npc_reactions", []):
            if isinstance(reaction, dict):
                reactions.append({
                    "character_id": reaction.get("character_id", ""),
                    "character_name": reaction.get("character_name", ""),
                    "dialogue": reaction.get("dialogue", ""),
                    "action": reaction.get("action", ""),
                    "emotion": reaction.get("emotion", "")
                })
        return reactions
    
    def save(self, save_name: str, at_boundary: bool = False) -> Path:
        """
        保存进度
        
        Args:
            save_name: 存档名称
            at_boundary: 是否在场景边界（幕间）。
                        True = 安全点，允许切换引擎
                        False = 场景中途（如 /quit），禁止切换
        """
        self.progress_tracker.save_progress(
            runtime_dir=self.runtime_dir, 
            current_scene_id=self.current_scene_id, 
            next_scene_id=self._next_scene_id,
            turn_count=self._total_turn_count,
            engine_type="osagent",
            can_switch_engine=at_boundary
        )
        self.invalidate_resume_cache()
        
        logger.info(f"游戏已保存: {save_name}, at_boundary={at_boundary}")
        return self.runtime_dir / "plot" / "progress.json"
    
    def get_status(self) -> SessionStatus:
        """获取当前会话状态"""
        ws_path = self.runtime_dir / "ws" / "world_state.json"
        location = ""
        current_time = ""
        present_characters = []
        
        if ws_path.exists():
            try:
                with open(ws_path, "r", encoding="utf-8") as f:
                    ws_data = json.load(f)
                    location = ws_data.get("location", {}).get("name", "")
                    current_time = ws_data.get("time", "")
                    present_characters = ws_data.get("present_characters", [])
            except Exception:
                pass
        
        return SessionStatus(
            scene_id=self.current_scene_id,
            turn_id=self._total_turn_count,
            location=location,
            current_time=current_time,
            present_characters=present_characters,
            can_continue=True
        )
    
    def get_action_suggestions(self) -> List[str]:
        """获取行动建议"""
        return [
            "观察周围环境",
            "与附近的人交谈"
        ]
    
    def _check_resume_state(self) -> Tuple[bool, Optional[str]]:
        """
        内部方法：检查恢复状态（带缓存）
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
        """使缓存失效"""
        if hasattr(self, '_resume_state_cache'):
            delattr(self, '_resume_state_cache')
    
    def can_resume(self) -> bool:
        """检查是否可以断点续传"""
        can_resume, _ = self._check_resume_state()
        return can_resume
    
    def get_resume_error(self) -> Optional[str]:
        """获取无法恢复的原因"""
        _, error = self._check_resume_state()
        return error
    
    def resume(self) -> str:
        """
        从断点恢复
        
        行为：
        1. 加载进度
        2. 初始化 Agent 和 NPC
        3. 运行初始场景循环（让 NPC 先说话，建立场景）
        4. 返回场景文本
        """
        # 初始化 Agent（损坏时 fail-fast）
        self._init_agents(fail_on_corrupted=True)
        
        # 初始化场景（NPC + 剧本）
        self._initialize_scene()
        
        # 创建场景记忆
        self._create_scene_memory()
        
        # 运行初始场景，让 NPC 先建立场景
        opening_text = self._run_initial_scene()
        
        logger.info(f"游戏恢复: scene={self.current_scene_id}, turn={self._total_turn_count}")
        
        # 返回场景文本，而不是简单的恢复提示
        return opening_text or (
            f"[RESUMED] Scene {self.current_scene_id}, Turn {self._total_turn_count}\n"
            f"Continuing your adventure..."
        )
