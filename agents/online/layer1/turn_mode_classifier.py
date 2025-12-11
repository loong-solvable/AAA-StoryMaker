"""
回合模式分类器 - 决定每个回合的处理模式

三种模式：
- DIALOGUE: 普通对话，仅调用NPC响应（快速路径）
- PLOT_ADVANCE: 剧情推进，完整调用WS+Plot+NPC
- ACT_TRANSITION: 幕转换，完整同步+切换幕
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import re

from utils.logger import setup_logger

logger = setup_logger("TurnModeClassifier", "turn_mode.log")


class TurnMode(Enum):
    """回合处理模式"""
    DIALOGUE = "dialogue"              # 普通对话（快速路径）
    PLOT_ADVANCE = "plot_advance"      # 剧情推进（完整路径）
    ACT_TRANSITION = "act_transition"  # 幕转换


@dataclass
class TurnContext:
    """回合上下文，用于模式判定"""
    player_input: str

    # 幕导演状态
    act_progress: float = 0.0          # 当前幕进度 (0-1)
    act_urgency: float = 0.0           # 紧迫度 (0-1)
    turns_in_act: int = 0              # 幕内已进行回合数
    max_turns: int = 10                # 幕最大回合数

    # 事件状态
    triggered_events: List[Dict] = field(default_factory=list)
    high_priority_event: bool = False  # 是否有高优先级事件

    # 累积状态
    dialogue_turns_since_plot: int = 0  # 上次Plot后的对话轮数

    # 位置变化
    location_changed: bool = False

    # NPC状态
    significant_npc_change: bool = False  # NPC情感是否有显著变化


class TurnModeClassifier:
    """
    回合模式分类器

    判定优先级：ACT_TRANSITION > PLOT_ADVANCE > DIALOGUE
    """

    # 触发PLOT_ADVANCE的关键词
    PLOT_ADVANCE_KEYWORDS = [
        # 行动类
        "走", "去", "离开", "进入", "移动", "前往",
        # 决策类
        "决定", "选择", "同意", "拒绝", "接受", "放弃",
        # 揭露类
        "告诉", "揭露", "坦白", "承认", "发现", "真相",
        # 冲突类
        "攻击", "战斗", "反抗", "威胁", "警告",
        # 关系类
        "表白", "道歉", "原谅", "承诺", "背叛"
    ]

    # 配置参数
    PROGRESS_THRESHOLD = 0.8          # 进度阈值
    URGENCY_THRESHOLD = 0.7           # 紧迫度阈值
    MAX_DIALOGUE_TURNS = 5            # 最大纯对话轮数
    EVENT_PRIORITY_THRESHOLD = 7      # 事件优先级阈值

    def __init__(
        self,
        act_director=None,
        event_engine=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化分类器

        Args:
            act_director: ActDirector实例
            event_engine: EventEngine实例
            config: 可选配置覆盖
        """
        self.act_director = act_director
        self.event_engine = event_engine

        # 应用自定义配置
        if config:
            self.PROGRESS_THRESHOLD = config.get("progress_threshold", self.PROGRESS_THRESHOLD)
            self.URGENCY_THRESHOLD = config.get("urgency_threshold", self.URGENCY_THRESHOLD)
            self.MAX_DIALOGUE_TURNS = config.get("max_dialogue_turns", self.MAX_DIALOGUE_TURNS)
            self.EVENT_PRIORITY_THRESHOLD = config.get("event_priority_threshold", self.EVENT_PRIORITY_THRESHOLD)

        # 内部状态跟踪
        self._dialogue_turns_since_plot = 0
        self._last_location: Optional[str] = None

        logger.info("TurnModeClassifier 初始化完成")

    def classify(self, context: TurnContext) -> TurnMode:
        """
        分类当前回合的处理模式

        Args:
            context: 回合上下文

        Returns:
            TurnMode: 处理模式
        """
        # 1. 最高优先级：幕转换检查
        if self._should_transition_act(context):
            logger.info(f"🎬 模式判定: ACT_TRANSITION (进度={context.act_progress:.2f})")
            return TurnMode.ACT_TRANSITION

        # 2. 中优先级：剧情推进检查
        if self._should_advance_plot(context):
            reason = self._get_plot_advance_reason(context)
            logger.info(f"📖 模式判定: PLOT_ADVANCE ({reason})")
            self._dialogue_turns_since_plot = 0  # 重置计数
            return TurnMode.PLOT_ADVANCE

        # 3. 默认：普通对话
        self._dialogue_turns_since_plot += 1
        logger.info(f"💬 模式判定: DIALOGUE (连续对话={self._dialogue_turns_since_plot})")
        return TurnMode.DIALOGUE

    def _should_transition_act(self, context: TurnContext) -> bool:
        """检查是否需要幕转换"""
        # 进度完成
        if context.act_progress >= 1.0:
            return True

        # 超时
        if context.turns_in_act >= context.max_turns:
            return True

        # 注：ActDirector.evaluate_progress 需要完整 game_state
        # 在分类阶段使用上面的简化判断即可
        return False

    def _should_advance_plot(self, context: TurnContext) -> bool:
        """检查是否需要剧情推进"""
        # 条件1：高优先级事件触发
        if context.high_priority_event:
            return True

        if context.triggered_events:
            for event in context.triggered_events:
                if event.get("priority", 0) >= self.EVENT_PRIORITY_THRESHOLD:
                    return True

        # 条件2：幕进度接近完成
        if context.act_progress >= self.PROGRESS_THRESHOLD:
            return True

        # 条件3：紧迫度较高
        if context.act_urgency >= self.URGENCY_THRESHOLD:
            return True

        # 条件4：连续对话轮数达到阈值
        if self._dialogue_turns_since_plot >= self.MAX_DIALOGUE_TURNS:
            return True

        # 条件5：位置变化
        if context.location_changed:
            return True

        # 条件6：玩家输入包含关键行动词
        if self._contains_plot_keywords(context.player_input):
            return True

        # 条件7：NPC情感显著变化
        if context.significant_npc_change:
            return True

        return False

    def _contains_plot_keywords(self, player_input: str) -> bool:
        """检查玩家输入是否包含剧情推进关键词"""
        for keyword in self.PLOT_ADVANCE_KEYWORDS:
            if keyword in player_input:
                return True
        return False

    def _get_plot_advance_reason(self, context: TurnContext) -> str:
        """获取触发PLOT_ADVANCE的原因（用于日志）"""
        reasons = []

        if context.high_priority_event or any(
            e.get("priority", 0) >= self.EVENT_PRIORITY_THRESHOLD
            for e in context.triggered_events
        ):
            reasons.append("高优先级事件")

        if context.act_progress >= self.PROGRESS_THRESHOLD:
            reasons.append(f"进度高={context.act_progress:.0%}")

        if context.act_urgency >= self.URGENCY_THRESHOLD:
            reasons.append(f"紧迫度高={context.act_urgency:.0%}")

        if self._dialogue_turns_since_plot >= self.MAX_DIALOGUE_TURNS:
            reasons.append(f"累积{self.MAX_DIALOGUE_TURNS}轮对话")

        if context.location_changed:
            reasons.append("位置变化")

        if self._contains_plot_keywords(context.player_input):
            reasons.append("关键行动")

        if context.significant_npc_change:
            reasons.append("NPC情感突变")

        return ", ".join(reasons) if reasons else "默认触发"

    def build_context(
        self,
        player_input: str,
        act_director=None,
        event_engine=None,
        current_location: Optional[str] = None,
        triggered_events: Optional[List[Dict]] = None,
        npc_manager=None
    ) -> TurnContext:
        """
        构建回合上下文

        Args:
            player_input: 玩家输入
            act_director: ActDirector实例
            event_engine: EventEngine实例
            current_location: 当前位置
            triggered_events: 已触发的事件列表
            npc_manager: NPCManager实例

        Returns:
            TurnContext: 构建好的上下文
        """
        ad = act_director or self.act_director
        ee = event_engine or self.event_engine

        # 从ActDirector获取幕状态
        act_progress = 0.0
        act_urgency = 0.0
        turns_in_act = 0
        max_turns = 10

        if ad and ad.current_act:
            act_progress = ad.current_act.progress
            turns_in_act = ad.current_act.turns_in_act
            if ad.current_act.objective:
                max_turns = ad.current_act.objective.max_turns
            # 根据回合进度计算紧迫度
            act_urgency = turns_in_act / max_turns if max_turns > 0 else 0.0

        # 检查位置变化
        location_changed = False
        if current_location and self._last_location:
            location_changed = current_location != self._last_location
        self._last_location = current_location

        # 检查事件优先级
        events = triggered_events or []
        high_priority_event = any(
            e.get("priority", 0) >= self.EVENT_PRIORITY_THRESHOLD
            for e in events
        )

        # 检查NPC情感变化
        significant_npc_change = False
        if npc_manager:
            significant_npc_change = self._check_significant_npc_change(npc_manager)

        return TurnContext(
            player_input=player_input,
            act_progress=act_progress,
            act_urgency=act_urgency,
            turns_in_act=turns_in_act,
            max_turns=max_turns,
            triggered_events=events,
            high_priority_event=high_priority_event,
            dialogue_turns_since_plot=self._dialogue_turns_since_plot,
            location_changed=location_changed,
            significant_npc_change=significant_npc_change
        )

    def _check_significant_npc_change(self, npc_manager) -> bool:
        """检查是否有NPC情感显著变化"""
        try:
            for npc_id, npc in npc_manager.npcs.items():
                # 检查情感变化是否超过阈值
                triggers = npc.emotional_state.get("emotional_triggers", [])
                if triggers:
                    last_trigger = triggers[-1]
                    if abs(last_trigger.get("attitude_change", 0)) > 0.15:
                        return True
        except Exception:
            pass
        return False

    def reset_dialogue_counter(self):
        """重置对话计数器（在PLOT_ADVANCE后调用）"""
        self._dialogue_turns_since_plot = 0

    def get_dialogue_turns_count(self) -> int:
        """获取当前连续对话轮数"""
        return self._dialogue_turns_since_plot
