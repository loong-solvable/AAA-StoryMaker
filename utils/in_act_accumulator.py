"""
幕内状态累积器 - 在幕内累积变化，幕结束时统一同步

功能：
1. 累积时间流逝（简化规则，每对话回合+3分钟）
2. 累积NPC状态变化（情感、态度）
3. 记录对话摘要（用于幕结束总结）
4. 幕结束时一次性同步到WS
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from utils.logger import setup_logger

logger = setup_logger("InActAccumulator", "accumulator.log")


@dataclass
class NPCStateDelta:
    """单个NPC的状态变化"""
    npc_id: str
    npc_name: str

    # 交互统计
    interaction_count: int = 0
    dialogue_count: int = 0

    # 情感变化
    mood_history: List[str] = field(default_factory=list)
    attitude_start: float = 0.5
    attitude_current: float = 0.5
    trust_start: float = 0.3
    trust_current: float = 0.3

    # 关键对话摘要
    key_dialogues: List[str] = field(default_factory=list)

    def record_interaction(
        self,
        dialogue: str,
        mood: str,
        attitude: float,
        trust: float,
        is_key: bool = False
    ):
        """记录一次交互"""
        self.interaction_count += 1
        if dialogue:
            self.dialogue_count += 1
            if is_key or len(self.key_dialogues) < 3:
                self.key_dialogues.append(dialogue[:80])

        if mood:
            self.mood_history.append(mood)
            if len(self.mood_history) > 5:
                self.mood_history = self.mood_history[-5:]

        self.attitude_current = attitude
        self.trust_current = trust

    @property
    def attitude_delta(self) -> float:
        """态度变化量"""
        return self.attitude_current - self.attitude_start

    @property
    def trust_delta(self) -> float:
        """信任度变化量"""
        return self.trust_current - self.trust_start

    @property
    def current_mood(self) -> str:
        """当前情绪"""
        return self.mood_history[-1] if self.mood_history else "平静"


@dataclass
class InActAccumulator:
    """
    幕内状态累积器

    在普通对话模式(DIALOGUE)中累积变化，
    在幕转换时(ACT_TRANSITION)一次性同步到WorldState
    """

    # 时间累积
    time_elapsed_minutes: int = 0
    base_time: Optional[datetime] = None

    # NPC状态变化
    npc_deltas: Dict[str, NPCStateDelta] = field(default_factory=dict)

    # 对话记录
    dialogue_log: List[Dict[str, Any]] = field(default_factory=list)

    # 回合计数
    turns_count: int = 0
    dialogue_turns: int = 0  # 纯对话回合数
    plot_turns: int = 0      # 剧情推进回合数

    # 玩家行为摘要
    player_actions: List[str] = field(default_factory=list)

    # 触发的事件记录
    triggered_events: List[Dict[str, Any]] = field(default_factory=list)

    # 场景上下文缓存（用于DIALOGUE模式复用）
    cached_scene_context: Optional[Dict[str, Any]] = None
    cached_scene_summary: str = ""

    def __post_init__(self):
        """初始化后处理"""
        if self.base_time is None:
            self.base_time = datetime.now()

    def record_dialogue_turn(
        self,
        player_input: str,
        npc_reactions: List[Dict[str, Any]],
        time_cost_minutes: int = 3
    ):
        """
        记录一个对话回合

        Args:
            player_input: 玩家输入
            npc_reactions: NPC反应列表
            time_cost_minutes: 时间消耗（分钟）
        """
        self.turns_count += 1
        self.dialogue_turns += 1
        self.time_elapsed_minutes += time_cost_minutes

        # 记录玩家行为
        self.player_actions.append(player_input[:50])
        if len(self.player_actions) > 20:
            self.player_actions = self.player_actions[-20:]

        # 记录对话
        turn_record = {
            "turn": self.turns_count,
            "player": player_input[:100],
            "npcs": [],
            "timestamp": self.get_current_time().isoformat()
        }

        # 处理每个NPC的反应
        for reaction_data in npc_reactions:
            npc = reaction_data.get("npc")
            reaction = reaction_data.get("reaction", {})

            if npc:
                self._accumulate_npc_reaction(npc, reaction)

                turn_record["npcs"].append({
                    "id": npc.character_id,
                    "name": npc.character_name,
                    "dialogue": reaction.get("dialogue", "")[:80],
                    "emotion": reaction.get("emotion", "")
                })

        self.dialogue_log.append(turn_record)
        if len(self.dialogue_log) > 30:
            self.dialogue_log = self.dialogue_log[-30:]

        logger.debug(f"记录对话回合 #{self.turns_count}, 累积时间={self.time_elapsed_minutes}分钟")

    def record_plot_turn(
        self,
        player_input: str,
        npc_reactions: List[Dict[str, Any]],
        world_update: Optional[Dict[str, Any]] = None,
        script: Optional[Dict[str, Any]] = None,
        time_cost_minutes: int = 10
    ):
        """
        记录一个剧情推进回合

        Args:
            player_input: 玩家输入
            npc_reactions: NPC反应列表
            world_update: 世界状态更新
            script: Plot生成的剧本
            time_cost_minutes: 时间消耗
        """
        self.turns_count += 1
        self.plot_turns += 1

        # 使用WS返回的时间增量
        if world_update:
            time_delta = world_update.get("time_delta_minutes", time_cost_minutes)
            self.time_elapsed_minutes += time_delta
        else:
            self.time_elapsed_minutes += time_cost_minutes

        # 记录玩家行为
        self.player_actions.append(player_input[:50])

        # 更新场景缓存
        if script:
            self.cached_scene_summary = script.get("director_notes", "")
            self.cached_scene_context = {
                "scene_theme": script.get("scene_theme", {}),
                "director_notes": script.get("director_notes", ""),
                "last_updated_turn": self.turns_count
            }

        # 记录NPC反应
        for reaction_data in npc_reactions:
            npc = reaction_data.get("npc")
            reaction = reaction_data.get("reaction", {})
            if npc:
                self._accumulate_npc_reaction(npc, reaction, is_plot_turn=True)

        logger.info(f"记录剧情回合 #{self.turns_count}, 累积时间={self.time_elapsed_minutes}分钟")

    def record_event(self, event: Dict[str, Any]):
        """记录触发的事件"""
        self.triggered_events.append({
            "event_id": event.get("event_id", ""),
            "event_name": event.get("event_name", ""),
            "turn": self.turns_count,
            "timestamp": self.get_current_time().isoformat()
        })

    def _accumulate_npc_reaction(
        self,
        npc,
        reaction: Dict[str, Any],
        is_plot_turn: bool = False
    ):
        """累积NPC状态变化"""
        npc_id = npc.character_id
        npc_name = npc.character_name

        # 获取或创建NPC状态记录
        if npc_id not in self.npc_deltas:
            self.npc_deltas[npc_id] = NPCStateDelta(
                npc_id=npc_id,
                npc_name=npc_name,
                attitude_start=npc.emotional_state.get("attitude_toward_player", 0.5),
                trust_start=npc.emotional_state.get("trust_level", 0.3)
            )

        delta = self.npc_deltas[npc_id]

        # 记录交互
        dialogue = reaction.get("dialogue", "")
        mood = reaction.get("emotion", npc.current_mood)
        attitude = npc.emotional_state.get("attitude_toward_player", 0.5)
        trust = npc.emotional_state.get("trust_level", 0.3)

        delta.record_interaction(
            dialogue=dialogue,
            mood=mood,
            attitude=attitude,
            trust=trust,
            is_key=is_plot_turn
        )

    def get_current_time(self) -> datetime:
        """获取累积后的当前时间"""
        if self.base_time:
            return self.base_time + timedelta(minutes=self.time_elapsed_minutes)
        return datetime.now()

    def get_current_time_str(self) -> str:
        """获取格式化的当前时间字符串"""
        return self.get_current_time().strftime("%Y-%m-%d %H:%M")

    def get_scene_context_for_npc(self) -> Dict[str, Any]:
        """
        获取用于NPC响应的场景上下文（DIALOGUE模式使用缓存）

        Returns:
            场景上下文字典
        """
        base_context = {
            "time": self.get_current_time_str(),
            "elapsed_minutes": self.time_elapsed_minutes,
            "turns_in_act": self.turns_count
        }

        if self.cached_scene_context:
            base_context.update({
                "scene_summary": self.cached_scene_summary,
                "mood": self.cached_scene_context.get("scene_theme", {}).get("mood", "平静")
            })
        else:
            base_context["mood"] = "平静"
            base_context["scene_summary"] = ""

        return base_context

    def get_act_summary(self) -> Dict[str, Any]:
        """
        获取幕内累积的摘要（用于幕转换时）

        Returns:
            幕摘要字典
        """
        # NPC交互统计
        npc_summaries = []
        for npc_id, delta in self.npc_deltas.items():
            npc_summaries.append({
                "npc_id": npc_id,
                "npc_name": delta.npc_name,
                "interaction_count": delta.interaction_count,
                "attitude_change": delta.attitude_delta,
                "trust_change": delta.trust_delta,
                "current_mood": delta.current_mood,
                "key_dialogues": delta.key_dialogues[-3:]
            })

        return {
            "total_turns": self.turns_count,
            "dialogue_turns": self.dialogue_turns,
            "plot_turns": self.plot_turns,
            "time_elapsed_minutes": self.time_elapsed_minutes,
            "player_actions_summary": self.player_actions[-10:],
            "npc_interactions": npc_summaries,
            "events_triggered": self.triggered_events
        }

    def flush_to_world_state(self, world_state_manager) -> Dict[str, Any]:
        """
        幕结束时同步累积状态到WorldState

        Args:
            world_state_manager: WorldStateManager实例

        Returns:
            同步结果
        """
        logger.info(f"开始同步幕内累积状态: {self.turns_count}回合, {self.time_elapsed_minutes}分钟")

        result = {
            "time_synced": False,
            "npc_synced": 0,
            "summary": self.get_act_summary()
        }

        try:
            # 1. 同步时间
            if hasattr(world_state_manager, '_advance_time'):
                world_state_manager._advance_time(self.time_elapsed_minutes)
                result["time_synced"] = True
            elif hasattr(world_state_manager, 'current_time'):
                # 直接更新时间
                if isinstance(world_state_manager.current_time, datetime):
                    world_state_manager.current_time += timedelta(minutes=self.time_elapsed_minutes)
                    result["time_synced"] = True

            # 2. 同步NPC状态
            for npc_id, delta in self.npc_deltas.items():
                try:
                    if hasattr(world_state_manager, 'npc_states') and npc_id in world_state_manager.npc_states:
                        ws_state = world_state_manager.npc_states[npc_id]
                        ws_state["mood"] = delta.current_mood
                        ws_state["attitude_toward_player"] = delta.attitude_current
                        ws_state["trust_level"] = delta.trust_current
                        result["npc_synced"] += 1
                except Exception as e:
                    logger.warning(f"同步NPC[{npc_id}]状态失败: {e}")

            logger.info(f"幕内状态同步完成: 时间={result['time_synced']}, NPC={result['npc_synced']}")

        except Exception as e:
            logger.error(f"同步幕内状态失败: {e}")

        return result

    def reset(self):
        """重置累积器（幕转换后调用）"""
        self.time_elapsed_minutes = 0
        self.base_time = datetime.now()
        self.npc_deltas.clear()
        self.dialogue_log.clear()
        self.turns_count = 0
        self.dialogue_turns = 0
        self.plot_turns = 0
        self.player_actions.clear()
        self.triggered_events.clear()
        self.cached_scene_context = None
        self.cached_scene_summary = ""

        logger.info("幕内累积器已重置")

    def update_scene_cache(self, scene_context: Dict[str, Any], scene_summary: str):
        """
        更新场景缓存（在PLOT_ADVANCE后调用）

        Args:
            scene_context: 新的场景上下文
            scene_summary: 新的场景摘要
        """
        self.cached_scene_context = scene_context
        self.cached_scene_summary = scene_summary

    def set_base_time(self, time_str: str):
        """
        设置基准时间（从WS获取）

        Args:
            time_str: 时间字符串，格式如 "2024-11-26 15:00"
        """
        try:
            self.base_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                self.base_time = datetime.fromisoformat(time_str)
            except ValueError:
                logger.warning(f"无法解析时间: {time_str}, 使用当前时间")
                self.base_time = datetime.now()
