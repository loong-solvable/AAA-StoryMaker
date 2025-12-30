"""
OS Agent 会话适配器

将 OS Agent 流程封装为统一的 GameSession 接口。

重要修复（v0.10.1）：
1. max_turns 问题：run_scene_loop(max_turns=1) 导致玩家输入无法进入场景循环
   - 修复：使用 max_turns=3 允许完整的 NPC→User→NPC 交互
2. 缺少 dispatch_script_to_actors() 调用：NPC 没有本幕目标/剧本
   - 修复：在 _initialize_scene_and_get_opening() 中调用
3. 字段名不匹配：run_scene_loop 返回 scene_finished，而代码检查 scene_ended
   - 修复：统一使用 scene_finished
4. 缺少幕间推进：未调用 process_scene_transition()
   - 修复：在场景结束时调用 process_scene_transition()
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
    
    def start(self) -> str:
        """
        开始新游戏
        
        行为：初始化 Agent + 初始化场景 + 分发剧本 + 返回开场文本
        
        注意：即使 progress.json 损坏，也使用默认进度继续（符合 Q4 规范）
        """
        self._init_agents(fail_on_corrupted=False)  # 新游戏不 fail-fast
        
        # 初始化场景（包括 NPC 初始化和剧本分发）
        opening_text = self._initialize_scene_and_get_opening()
        
        logger.info(f"游戏开始: scene={self.current_scene_id}, world={self.world_dir.name}")
        
        return opening_text
    
    def _initialize_scene_and_get_opening(self) -> str:
        """
        初始化场景并获取开场文本
        
        关键流程：
        1. 确保 NPC 已初始化 (ensure_scene_characters_initialized)
        2. 分发剧本给 NPC (dispatch_script_to_actors) ← 关键！
        3. 读取场景信息返回开场文本
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
        
        # 3. 读取场景信息
        scene_desc = ""
        location = ""
        script_path = self.runtime_dir / "plot" / "current_script.json"
        if script_path.exists():
            try:
                with open(script_path, "r", encoding="utf-8") as f:
                    script_data = json.load(f)
                    scene_desc = script_data.get("scene_description", "")
                    location = script_data.get("location_name", "")
            except Exception as e:
                logger.warning(f"读取场景信息失败: {e}")
        
        # 4. 构建开场文本
        result = f"[Scene {self.current_scene_id}]"
        if location:
            result += f"\nLocation: {location}"
        if scene_desc:
            result += f"\n\n{scene_desc}"
        result += "\n\nAre you ready to begin your adventure?"
        
        return result
    
    def process_turn(self, player_input: str) -> TurnResult:
        """
        处理一个回合
        
        使用 run_scene_loop 进行完整的场景交互：
        - max_turns=3 允许 NPC→User→NPC 的完整交互
        - 玩家输入通过 user_input_callback 传递
        - 使用 scene_finished（不是 scene_ended）检测边界
        """
        # 回合开始时立即持久化，禁止切换引擎（防止重启后允许不安全切换）
        self.progress_tracker.save_progress(
            runtime_dir=self.runtime_dir,
            current_scene_id=self.current_scene_id,
            next_scene_id=self._next_scene_id,
            turn_count=self._total_turn_count,
            engine_type="osagent",
            can_switch_engine=False  # 回合中禁止切换
        )
        self.invalidate_resume_cache()
        
        try:
            # 确保 NPC 已初始化
            self.os_agent.ensure_scene_characters_initialized(
                runtime_dir=self.runtime_dir,
                world_dir=self.world_dir
            )
            
            # 使用 run_scene_loop 进行场景交互
            # max_turns=3: NPC 开场 → 玩家输入 → NPC 响应
            loop_result = self.os_agent.run_scene_loop(
                runtime_dir=self.runtime_dir,
                world_dir=self.world_dir,
                max_turns=3,  # 允许完整的交互循环
                user_input_callback=lambda _: player_input,
                screen_callback=self._screen_callback
            )
            
            # 累加回合数
            turns_this_call = loop_result.get("total_turns", 1)
            self._total_turn_count += turns_this_call
            
            # 检测是否到达场景边界（幕间）
            # 注意：run_scene_loop 返回的是 scene_finished，不是 scene_ended
            is_success = loop_result.get("success", False)
            is_scene_boundary = is_success and loop_result.get("scene_finished", False)
            
            # 如果场景结束，处理幕间过渡
            if is_scene_boundary:
                self._handle_scene_transition()
            
            # 回合结束后落盘（边界时允许切换，否则禁止）
            self.progress_tracker.save_progress(
                runtime_dir=self.runtime_dir,
                current_scene_id=self.current_scene_id,
                next_scene_id=self._next_scene_id,
                turn_count=self._total_turn_count,
                engine_type="osagent",
                can_switch_engine=is_scene_boundary  # 仅边界时允许切换
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
        """
        try:
            # 调用 OS Agent 的幕间处理
            if hasattr(self.os_agent, 'process_scene_transition'):
                transition_result = self.os_agent.process_scene_transition(
                    runtime_dir=self.runtime_dir,
                    world_dir=self.world_dir
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
                    logger.info(f"幕间过渡完成: 进入第 {self.current_scene_id} 幕")
                else:
                    logger.warning(f"幕间过渡失败: {transition_result.get('error')}")
            else:
                # 简单推进
                self.current_scene_id += 1
                self._next_scene_id = self.current_scene_id + 1
                logger.info(f"简单幕间推进: 进入第 {self.current_scene_id} 幕")
                
        except Exception as e:
            logger.error(f"幕间过渡异常: {e}", exc_info=True)
            # 即使失败也推进场景，避免卡住
            self.current_scene_id += 1
            self._next_scene_id = self.current_scene_id + 1
    
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
            can_switch_engine=at_boundary  # 仅边界时允许切换
        )
        # 保存后使缓存失效，允许后续重新检测（如返回菜单再次检查）
        self.invalidate_resume_cache()
        
        logger.info(f"游戏已保存: {save_name}, at_boundary={at_boundary}")
        return self.runtime_dir / "plot" / "progress.json"
    
    def get_status(self) -> SessionStatus:
        """获取当前会话状态"""
        # 读取世界状态
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
        # 简化实现，实际应调用 ActionSuggester
        return [
            "观察周围环境",
            "与附近的人交谈"
        ]
    
    def _check_resume_state(self) -> Tuple[bool, Optional[str]]:
        """
        内部方法：检查恢复状态（带缓存，避免 load_progress 副作用）
        
        重要：load_progress() 在检测到损坏时会重命名文件，
        因此必须缓存首次检查结果，后续调用直接返回缓存。
        
        Returns:
            (can_resume, error_message)
        """
        # 使用实例级缓存，避免重复调用
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
        从断点恢复
        
        行为规范：
        1. 加载 progress.json 恢复 scene_id 和 turn_count
        2. 初始化 OS Agent（不重新生成开场剧本）
        3. 确保 NPC 初始化和剧本分发
        4. 返回恢复提示文本（而非完整开场）
        
        与 start() 的区别：
        - start() = _init_agents(fail_on_corrupted=False) + 完整初始化 + 开场文本
        - resume() = _init_agents(fail_on_corrupted=True) + NPC初始化 + 恢复提示
        
        前置条件：can_resume() 返回 True
        Raises：RuntimeError 如果 progress.json 损坏
        """
        # 仅初始化 Agent（损坏时 fail-fast）
        self._init_agents(fail_on_corrupted=True)
        
        # 确保 NPC 已初始化
        self.os_agent.ensure_scene_characters_initialized(
            runtime_dir=self.runtime_dir,
            world_dir=self.world_dir
        )
        
        # 分发剧本给 NPC
        try:
            self.os_agent.dispatch_script_to_actors(self.runtime_dir)
        except Exception as e:
            logger.warning(f"恢复时剧本分发失败: {e}")
        
        logger.info(f"游戏恢复: scene={self.current_scene_id}, turn={self._total_turn_count}")
        
        # 返回恢复提示而非开场文本
        return (
            f"[RESUMED] Restored from checkpoint\n"
            f"   Scene: {self.current_scene_id}\n"
            f"   Total turns: {self._total_turn_count}\n"
            f"   Continuing your adventure..."
        )
