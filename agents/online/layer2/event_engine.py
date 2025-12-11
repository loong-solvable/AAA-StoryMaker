"""
事件引擎 (Event Engine)
管理条件/时间/概率触发的游戏事件，增加世界的动态性
"""
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger("EventEngine", "event_engine.log")


@dataclass
class EventTrigger:
    """事件触发条件"""
    trigger_type: str  # "time"|"condition"|"probability"|"manual"

    # 时间触发
    trigger_time: Optional[str] = None  # "2024-11-26 18:00" 格式
    time_after_turns: Optional[int] = None  # N回合后触发

    # 条件触发
    conditions: List[Dict] = field(default_factory=list)
    # 条件格式: {"type": "flag"|"npc_mood"|"location"|"turns_elapsed", ...}

    # 概率触发
    probability: float = 0.0  # 0-1，每回合触发概率
    probability_cooldown: int = 0  # 触发后冷却回合数


@dataclass
class GameEvent:
    """游戏事件定义"""
    event_id: str
    event_name: str
    description: str
    trigger: EventTrigger
    priority: int = 5  # 1-10，≥8可打断正常流程

    # 事件效果
    effects: List[Dict] = field(default_factory=list)
    # 效果格式: {"type": "set_flag"|"npc_mood"|"spawn_npc", ...}

    plot_override: Optional[str] = None  # 强制剧情（可打断正常流程）
    npc_reactions: Dict[str, str] = field(default_factory=dict)  # NPC被动反应

    # 元数据
    is_repeatable: bool = False
    has_triggered: bool = False
    cooldown_remaining: int = 0
    triggered_at_turn: Optional[int] = None


class EventEngine:
    """
    事件引擎 - 管理条件触发的游戏事件

    核心职责:
    1. 检查事件触发条件
    2. 应用事件效果到游戏状态
    3. 支持Genesis预定义事件和运行时动态事件
    4. 与ActDirector和Plot协作
    """

    def __init__(self, genesis_data: Dict[str, Any]):
        """
        初始化事件引擎

        Args:
            genesis_data: Genesis世界数据，包含可选的 event_definitions
        """
        logger.info("⚡ 初始化事件引擎...")

        # 加载预定义事件
        self.event_definitions: List[GameEvent] = []
        raw_events = genesis_data.get("event_definitions", [])
        for raw in raw_events:
            event = self._parse_event_definition(raw)
            if event:
                self.event_definitions.append(event)

        # 利用现有social_logic作为规则基础
        social_logic = genesis_data.get("world", {}).get("social_logic", [])
        if not social_logic:
            # 尝试从world_setting中获取
            world_setting = genesis_data.get("world_setting", {})
            social_logic = world_setting.get("social_logic", [])

        social_events = self._convert_social_logic_to_events(social_logic)
        self.event_definitions.extend(social_events)

        # 运行时动态事件
        self.dynamic_events: List[GameEvent] = []

        # 游戏标记（全局状态）
        self.game_flags: Dict[str, Any] = {}

        # 触发历史
        self.triggered_history: List[Dict] = []

        # 当前回合
        self.current_turn: int = 0

        logger.info(f"✅ 事件引擎初始化完成")
        logger.info(f"   - 预定义事件: {len(self.event_definitions)}")
        logger.info(f"   - 社会规则事件: {len(social_events)}")

    def _parse_event_definition(self, raw: Dict[str, Any]) -> Optional[GameEvent]:
        """解析事件定义"""
        try:
            trigger_raw = raw.get("trigger", {})
            trigger = EventTrigger(
                trigger_type=trigger_raw.get("trigger_type", "condition"),
                trigger_time=trigger_raw.get("trigger_time"),
                time_after_turns=trigger_raw.get("time_after_turns"),
                conditions=trigger_raw.get("conditions", []),
                probability=trigger_raw.get("probability", 0.0),
                probability_cooldown=trigger_raw.get("probability_cooldown", 0)
            )

            return GameEvent(
                event_id=raw.get("event_id", f"evt_{len(self.event_definitions)}"),
                event_name=raw.get("event_name", "未命名事件"),
                description=raw.get("description", ""),
                trigger=trigger,
                priority=raw.get("priority", 5),
                effects=raw.get("effects", []),
                plot_override=raw.get("plot_override"),
                npc_reactions=raw.get("npc_reactions", {}),
                is_repeatable=raw.get("is_repeatable", False)
            )
        except Exception as e:
            logger.warning(f"⚠️ 解析事件定义失败: {e}")
            return None

    def _convert_social_logic_to_events(self, social_logic: List[Dict]) -> List[GameEvent]:
        """将social_logic规则转换为事件定义"""
        events = []
        for i, rule in enumerate(social_logic):
            trigger_condition = rule.get("trigger_condition", "")
            consequence = rule.get("consequence", "")

            if not trigger_condition:
                continue

            event = GameEvent(
                event_id=f"social_{i}",
                event_name=rule.get("rule_name", f"社会规则_{i}"),
                description=consequence,
                trigger=EventTrigger(
                    trigger_type="condition",
                    conditions=[
                        {"type": "narrative_condition", "text": trigger_condition}
                    ]
                ),
                priority=8 if rule.get("is_rigid") else 5,
                effects=[],
                plot_override=None,  # 社会规则不强制覆盖剧情
                is_repeatable=True  # 社会规则可重复触发
            )
            events.append(event)

        return events

    def check_triggers(
        self,
        game_state: Dict[str, Any],
        current_time: str,
        turn_number: int
    ) -> List[GameEvent]:
        """
        检查所有事件的触发条件

        Args:
            game_state: 当前游戏状态
            current_time: 当前游戏时间
            turn_number: 当前回合数

        Returns:
            本回合触发的事件列表（按优先级排序）
        """
        self.current_turn = turn_number
        triggered = []

        # 更新冷却
        self._update_cooldowns()

        # 检查所有事件
        all_events = self.event_definitions + self.dynamic_events

        for event in all_events:
            if self._should_trigger(event, game_state, current_time, turn_number):
                triggered.append(event)
                event.has_triggered = True
                event.triggered_at_turn = turn_number

                # 设置冷却
                if event.trigger.probability_cooldown > 0:
                    event.cooldown_remaining = event.trigger.probability_cooldown

                # 记录历史
                self.triggered_history.append({
                    "event_id": event.event_id,
                    "event_name": event.event_name,
                    "turn": turn_number,
                    "timestamp": datetime.now().isoformat()
                })

                logger.info(f"⚡ 事件触发: [{event.event_id}] {event.event_name} (优先级:{event.priority})")

        # 按优先级排序（高优先级在前）
        triggered.sort(key=lambda e: e.priority, reverse=True)
        return triggered

    def _update_cooldowns(self):
        """更新所有事件的冷却计数"""
        for event in self.event_definitions + self.dynamic_events:
            if event.cooldown_remaining > 0:
                event.cooldown_remaining -= 1

    def _should_trigger(
        self,
        event: GameEvent,
        game_state: Dict[str, Any],
        current_time: str,
        turn_number: int
    ) -> bool:
        """检查单个事件是否应该触发"""
        # 已触发且不可重复
        if event.has_triggered and not event.is_repeatable:
            return False

        # 冷却中
        if event.cooldown_remaining > 0:
            return False

        trigger = event.trigger

        if trigger.trigger_type == "time":
            return self._check_time_trigger(trigger, current_time, turn_number)
        elif trigger.trigger_type == "condition":
            return self._check_condition_trigger(trigger, game_state)
        elif trigger.trigger_type == "probability":
            return self._check_probability_trigger(trigger)
        elif trigger.trigger_type == "manual":
            return False  # 手动触发需要显式调用

        return False

    def _check_time_trigger(
        self,
        trigger: EventTrigger,
        current_time: str,
        turn_number: int
    ) -> bool:
        """检查时间触发"""
        # 检查具体时间
        if trigger.trigger_time:
            try:
                target = datetime.strptime(trigger.trigger_time, "%Y-%m-%d %H:%M")
                current = datetime.strptime(current_time, "%Y-%m-%d %H:%M")
                if current >= target:
                    return True
            except ValueError:
                pass

        # 检查回合数触发
        if trigger.time_after_turns is not None:
            if turn_number >= trigger.time_after_turns:
                return True

        return False

    def _check_condition_trigger(self, trigger: EventTrigger, game_state: Dict[str, Any]) -> bool:
        """检查条件触发"""
        for cond in trigger.conditions:
            cond_type = cond.get("type")

            if cond_type == "flag":
                # 检查游戏标记
                flag_name = cond.get("flag")
                expected_value = cond.get("value", True)
                if self.game_flags.get(flag_name) != expected_value:
                    return False

            elif cond_type == "npc_mood":
                # 检查NPC情绪
                npc_id = cond.get("npc_id")
                expected_mood = cond.get("mood")
                npc_states = game_state.get("npc_states", {})
                actual_mood = npc_states.get(npc_id, {}).get("mood")
                if actual_mood != expected_mood:
                    return False

            elif cond_type == "location":
                # 检查玩家位置
                expected_location = cond.get("location")
                actual_location = game_state.get("player_location")
                if actual_location != expected_location:
                    return False

            elif cond_type == "turns_elapsed":
                # 检查回合数
                min_turns = cond.get("min_turns", 0)
                if self.current_turn < min_turns:
                    return False

            elif cond_type == "narrative_condition":
                # 叙事条件（需要Plot判断，这里简化处理）
                # 在实际实现中，可以通过LLM判断条件是否满足
                pass

            # 未知条件类型，跳过
            else:
                logger.debug(f"未知条件类型: {cond_type}")

        return True

    def _check_probability_trigger(self, trigger: EventTrigger) -> bool:
        """检查概率触发"""
        if trigger.probability <= 0:
            return False
        return random.random() < trigger.probability

    def apply_effects(self, event: GameEvent, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        应用事件效果到游戏状态

        Args:
            event: 触发的事件
            game_state: 当前游戏状态

        Returns:
            更新后的效果摘要
        """
        effects_applied = []

        for effect in event.effects:
            effect_type = effect.get("type")

            if effect_type == "set_flag":
                # 设置游戏标记
                flag_name = effect.get("flag")
                value = effect.get("value", True)
                self.game_flags[flag_name] = value
                effects_applied.append(f"设置标记 {flag_name}={value}")

            elif effect_type == "npc_mood":
                # 更新NPC情绪（返回给调用者处理）
                npc_id = effect.get("npc_id")
                mood = effect.get("mood")
                effects_applied.append(f"NPC {npc_id} 情绪变为 {mood}")

            elif effect_type == "spawn_npc":
                # 生成NPC到场景（返回给调用者处理）
                npc_id = effect.get("npc_id")
                location = effect.get("location", game_state.get("player_location"))
                effects_applied.append(f"NPC {npc_id} 出现在 {location}")

            elif effect_type == "trigger_act_transition":
                # 触发幕转换
                outcome = effect.get("outcome", "success")
                effects_applied.append(f"触发幕转换: {outcome}")

            elif effect_type == "add_plot_hint":
                # 添加剧情提示
                hint = effect.get("hint", "")
                effects_applied.append(f"剧情提示: {hint}")

        logger.info(f"📋 应用事件效果: {', '.join(effects_applied) if effects_applied else '无效果'}")

        return {
            "event_id": event.event_id,
            "effects_applied": effects_applied,
            "plot_override": event.plot_override,
            "npc_reactions": event.npc_reactions
        }

    def set_flag(self, flag_name: str, value: Any):
        """设置游戏标记（供外部调用）"""
        self.game_flags[flag_name] = value
        logger.debug(f"🚩 设置标记: {flag_name} = {value}")

    def get_flag(self, flag_name: str, default: Any = None) -> Any:
        """获取游戏标记"""
        return self.game_flags.get(flag_name, default)

    def add_dynamic_event(self, event_definition: Dict[str, Any]):
        """
        添加运行时动态事件

        Args:
            event_definition: 事件定义字典
        """
        event = self._parse_event_definition(event_definition)
        if event:
            self.dynamic_events.append(event)
            logger.info(f"📝 添加动态事件: {event.event_name}")

    def trigger_manual_event(self, event_id: str) -> Optional[GameEvent]:
        """
        手动触发指定事件

        Args:
            event_id: 事件ID

        Returns:
            触发的事件，如果找不到则返回None
        """
        for event in self.event_definitions + self.dynamic_events:
            if event.event_id == event_id:
                if event.has_triggered and not event.is_repeatable:
                    logger.warning(f"⚠️ 事件 {event_id} 已触发且不可重复")
                    return None

                event.has_triggered = True
                event.triggered_at_turn = self.current_turn

                self.triggered_history.append({
                    "event_id": event.event_id,
                    "event_name": event.event_name,
                    "turn": self.current_turn,
                    "timestamp": datetime.now().isoformat(),
                    "manual": True
                })

                logger.info(f"⚡ 手动触发事件: {event.event_name}")
                return event

        logger.warning(f"⚠️ 找不到事件: {event_id}")
        return None

    def get_pending_high_priority_events(self) -> List[GameEvent]:
        """获取待处理的高优先级事件（优先级≥8）"""
        return [
            event for event in self.event_definitions + self.dynamic_events
            if event.has_triggered and event.priority >= 8
        ]

    def get_triggered_events_this_turn(self, turn_number: int) -> List[Dict]:
        """获取指定回合触发的事件"""
        return [
            record for record in self.triggered_history
            if record.get("turn") == turn_number
        ]

    def get_state_snapshot(self) -> Dict[str, Any]:
        """获取状态快照（用于持久化）"""
        return {
            "game_flags": dict(self.game_flags),
            "current_turn": self.current_turn,
            "triggered_count": len(self.triggered_history),
            "recent_triggers": self.triggered_history[-10:],  # 最近10个
            "event_definitions_count": len(self.event_definitions),
            "dynamic_events_count": len(self.dynamic_events)
        }

    def sync_flags_with_act_director(self, act_director_flags: Dict[str, Any]):
        """
        与ActDirector同步标记

        Args:
            act_director_flags: ActDirector的游戏标记
        """
        # 双向同步，事件引擎的标记优先
        for key, value in act_director_flags.items():
            if key not in self.game_flags:
                self.game_flags[key] = value
