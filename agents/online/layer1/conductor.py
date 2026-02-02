"""
Conductor（中枢指挥家）
合并 ActDirector + EventEngine + TurnModeClassifier
管控幕节奏、事件触发、模式判断、NPC幕级视野
"""
import asyncio
import random
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

from utils.logger import setup_logger
from utils.llm_factory import get_llm

logger = setup_logger("Conductor", "conductor.log")


# ============================================================
# 枚举和数据结构
# ============================================================

class TurnMode(Enum):
    """回合处理模式"""
    DIALOGUE = "dialogue"              # 普通对话（快速路径）
    PLOT_ADVANCE = "plot_advance"      # 剧情推进（完整路径）
    ACT_TRANSITION = "act_transition"  # 幕转换


class DialoguePhase(Enum):
    """对话阶段"""
    OPENING = "opening"      # 开场
    RISING = "rising"        # 发展
    CLIMAX = "climax"        # 高潮
    FALLING = "falling"      # 收尾


@dataclass
class TurnDecision:
    """回合决策结果"""
    mode: TurnMode
    decision_layer: int               # 0=规则/1=缓存/2=实时LLM
    confidence: float = 1.0

    # NPC焦点
    focal_npcs: List[str] = field(default_factory=list)
    observer_npcs: List[str] = field(default_factory=list)

    # 场景情绪
    scene_mood: str = "平静"
    tension_level: float = 0.3

    # 对话阶段
    dialogue_phase: DialoguePhase = DialoguePhase.OPENING
    phase_guidance: str = ""

    # 额外信息
    triggered_events: List[Any] = field(default_factory=list)
    should_advance_reason: str = ""


@dataclass
class TurnPrediction:
    """异步预判结果（缓存）"""
    predicted_mode: TurnMode = TurnMode.DIALOGUE
    confidence: float = 0.5
    focal_npcs: List[str] = field(default_factory=list)
    scene_mood: str = "平静"
    tension_level: float = 0.3
    dialogue_phase: DialoguePhase = DialoguePhase.OPENING
    phase_guidance: str = ""
    is_valid: bool = False  # 是否有效


@dataclass
class ActObjective:
    """幕目标定义"""
    objective_id: str
    description: str                            # 目标描述（给玩家看）
    internal_goal: str                          # 内部目标（给Plot用）
    completion_conditions: List[Dict] = field(default_factory=list)
    failure_conditions: List[Dict] = field(default_factory=list)
    max_turns: int = 15
    urgency_curve: str = "linear"
    plot_guidance: str = ""


@dataclass
class ActState:
    """幕状态"""
    act_number: int
    act_name: str
    objective: ActObjective
    turns_in_act: int = 0
    progress: float = 0.0
    completion_flags: Dict[str, bool] = field(default_factory=dict)
    is_complete: bool = False
    outcome: str = "ongoing"  # success/failure/timeout/ongoing
    started_at: str = ""
    ended_at: str = ""


@dataclass
class NPCActBriefing:
    """单个NPC的幕级指令"""
    npc_id: str
    npc_name: str
    role_in_act: str = "参与者"              # 引导者/阻碍者/旁观者/参与者
    knowledge_scope: List[str] = field(default_factory=list)
    forbidden_knowledge: List[str] = field(default_factory=list)
    emotional_journey: str = ""              # "从冷漠到好奇"
    key_lines: List[str] = field(default_factory=list)


@dataclass
class ActContext:
    """幕级上下文"""
    act_number: int
    act_name: str
    act_theme: str = ""
    act_goal_for_player: str = ""
    act_goal_internal: str = ""
    npc_briefings: Dict[str, NPCActBriefing] = field(default_factory=dict)
    key_reveals: List[str] = field(default_factory=list)
    forbidden_reveals: List[str] = field(default_factory=list)
    emotional_arc: str = ""
    target_ending_mood: str = ""


@dataclass
class EventTrigger:
    """事件触发条件"""
    trigger_type: str  # time/condition/probability/manual
    trigger_time: Optional[str] = None
    time_after_turns: Optional[int] = None
    conditions: List[Dict] = field(default_factory=list)
    probability: float = 0.0
    probability_cooldown: int = 0


@dataclass
class GameEvent:
    """游戏事件"""
    event_id: str
    event_name: str
    description: str
    trigger: EventTrigger
    priority: int = 5  # 1-10, ≥8 可打断正常流程
    effects: List[Dict] = field(default_factory=list)
    plot_override: Optional[str] = None
    npc_reactions: Dict[str, str] = field(default_factory=dict)
    is_repeatable: bool = False
    has_triggered: bool = False
    cooldown_remaining: int = 0
    triggered_at_turn: Optional[int] = None


# ============================================================
# Conductor 主类
# ============================================================

class Conductor:
    """
    中枢指挥家 - 管控幕节奏和NPC视野

    职责：
    1. 三层决策模型判断回合模式
    2. 幕进度管理（原ActDirector）
    3. 事件触发（原EventEngine）
    4. 异步预判下一回合
    5. NPC幕级视野管理
    """

    # 显式触发词（Layer 0 规则）
    EXPLICIT_PLOT_TRIGGERS = [
        "我要离开", "离开这里", "前往", "去",
        "开始战斗", "攻击", "战斗",
        "我决定", "我选择", "我同意", "我拒绝"
    ]

    EXPLICIT_TRANSITION_TRIGGERS = [
        "结束", "告辞", "再见", "下一章"
    ]

    def __init__(
        self,
        genesis_data: Dict[str, Any],
        llm=None,
        enable_async_predict: bool = True
    ):
        """
        初始化 Conductor

        Args:
            genesis_data: Genesis世界数据
            llm: LLM实例（用于异步预判和NPC幕剧本生成）
            enable_async_predict: 是否启用异步预判
        """
        logger.info("🎭 初始化 Conductor（中枢指挥家）...")

        self.genesis_data = genesis_data
        self.llm = llm or get_llm()
        self.enable_async_predict = enable_async_predict

        # ========== 幕管理（原ActDirector）==========
        self.act_definitions: List[Dict] = genesis_data.get("act_definitions", [])
        if not self.act_definitions:
            self.act_definitions = self._create_default_acts()
            logger.info("📝 未找到预定义幕目标，使用默认三幕结构")

        self.current_act: Optional[ActState] = None
        self.act_history: List[ActState] = []
        self.current_act_context: Optional[ActContext] = None

        # 幕进度追踪
        self.npc_interaction_count: Dict[str, int] = {}
        self.locations_visited: List[str] = []
        self.key_events_occurred: List[str] = []

        # ========== 事件管理（原EventEngine）==========
        self.event_definitions: List[GameEvent] = []
        raw_events = genesis_data.get("event_definitions", [])
        for raw in raw_events:
            event = self._parse_event_definition(raw)
            if event:
                self.event_definitions.append(event)

        # 社会规则转事件
        social_logic = genesis_data.get("world", {}).get("social_logic", [])
        if not social_logic:
            world_setting = genesis_data.get("world_setting", {})
            social_logic = world_setting.get("social_logic", [])
        social_events = self._convert_social_logic_to_events(social_logic)
        self.event_definitions.extend(social_events)

        self.dynamic_events: List[GameEvent] = []
        self.triggered_history: List[Dict] = []

        # ========== 全局状态 ==========
        self.game_flags: Dict[str, Any] = {}
        self.current_turn: int = 0

        # ========== 对话追踪 ==========
        self.dialogue_turns_since_plot: int = 0
        self.last_location: Optional[str] = None
        self.dialogue_phase: DialoguePhase = DialoguePhase.OPENING
        self.phase_turn_count: int = 0

        # ========== 异步预判 ==========
        self.cached_prediction: TurnPrediction = TurnPrediction()
        self._prediction_task: Optional[asyncio.Task] = None

        # ========== NPC幕级视野 ==========
        self.npc_act_briefings: Dict[str, NPCActBriefing] = {}

        # ========== 初始化第一幕 ==========
        self._initialize_first_act()

        logger.info(f"✅ Conductor 初始化完成")
        logger.info(f"   - 预定义幕数: {len(self.act_definitions)}")
        logger.info(f"   - 预定义事件: {len(self.event_definitions)}")
        logger.info(f"   - 当前幕: {self.current_act.act_name if self.current_act else 'None'}")

    # ============================================================
    # 核心决策接口
    # ============================================================

    def decide_turn_mode(
        self,
        player_input: str,
        game_context: Dict[str, Any]
    ) -> TurnDecision:
        """
        三层决策模型判断回合模式

        Layer 0: 规则快判（0延迟）
        Layer 1: 缓存预判（0延迟，使用上回合异步结果）
        Layer 2: 实时LLM判断（仅高紧迫度时）

        Args:
            player_input: 玩家输入
            game_context: 游戏上下文 {
                player_location, present_npcs, recent_dialogue,
                npc_states, ...
            }

        Returns:
            TurnDecision
        """
        # 检查事件触发
        triggered_events = self.check_triggers(
            game_state=game_context,
            current_time=game_context.get("current_time", ""),
            turn_number=self.current_turn
        )

        # 构建决策上下文
        context = self._build_decision_context(player_input, game_context, triggered_events)

        # ========== Layer 0: 规则快判 ==========
        layer0_result = self._layer0_rule_check(player_input, context, triggered_events)
        if layer0_result:
            logger.info(f"🎯 Layer 0 决策: {layer0_result.mode.value} ({layer0_result.should_advance_reason})")
            return layer0_result

        # ========== Layer 1: 缓存预判 ==========
        if self.cached_prediction.is_valid:
            layer1_result = self._layer1_cached_prediction(context, triggered_events)
            if layer1_result:
                logger.info(f"🎯 Layer 1 决策: {layer1_result.mode.value} (缓存预判)")
                return layer1_result

        # ========== Layer 2: 默认DIALOGUE ==========
        # 注：高紧迫度时的实时LLM判断可在此扩展
        default_result = self._create_dialogue_decision(context, triggered_events)
        logger.info(f"🎯 Layer 2 决策: {default_result.mode.value} (默认)")
        return default_result

    def _layer0_rule_check(
        self,
        player_input: str,
        context: Dict[str, Any],
        triggered_events: List[GameEvent]
    ) -> Optional[TurnDecision]:
        """Layer 0: 规则快判"""

        # 1. 检查幕转换条件
        if context["progress"] >= 1.0 or context["turns_in_act"] >= context["max_turns"]:
            return TurnDecision(
                mode=TurnMode.ACT_TRANSITION,
                decision_layer=0,
                triggered_events=triggered_events,
                should_advance_reason="幕目标完成或超时"
            )

        # 2. 检查显式转换触发词
        for trigger in self.EXPLICIT_TRANSITION_TRIGGERS:
            if trigger in player_input:
                return TurnDecision(
                    mode=TurnMode.ACT_TRANSITION,
                    decision_layer=0,
                    triggered_events=triggered_events,
                    should_advance_reason=f"显式触发词: {trigger}"
                )

        # 3. 检查高优先级事件（≥8）
        high_priority_events = [e for e in triggered_events if e.priority >= 8]
        if high_priority_events:
            return TurnDecision(
                mode=TurnMode.PLOT_ADVANCE,
                decision_layer=0,
                triggered_events=triggered_events,
                should_advance_reason=f"高优先级事件: {high_priority_events[0].event_name}"
            )

        # 4. 检查显式剧情触发词
        for trigger in self.EXPLICIT_PLOT_TRIGGERS:
            if trigger in player_input:
                return TurnDecision(
                    mode=TurnMode.PLOT_ADVANCE,
                    decision_layer=0,
                    triggered_events=triggered_events,
                    should_advance_reason=f"显式触发词: {trigger}"
                )

        # 5. 检查位置变化
        if context.get("location_changed"):
            return TurnDecision(
                mode=TurnMode.PLOT_ADVANCE,
                decision_layer=0,
                triggered_events=triggered_events,
                should_advance_reason="位置变化"
            )

        # 6. 检查累积对话轮数（超过5轮强制PLOT_ADVANCE）
        if self.dialogue_turns_since_plot >= 5:
            return TurnDecision(
                mode=TurnMode.PLOT_ADVANCE,
                decision_layer=0,
                triggered_events=triggered_events,
                should_advance_reason=f"累积{self.dialogue_turns_since_plot}轮对话"
            )

        return None

    def _layer1_cached_prediction(
        self,
        context: Dict[str, Any],
        triggered_events: List[GameEvent]
    ) -> Optional[TurnDecision]:
        """Layer 1: 使用缓存的异步预判结果"""
        pred = self.cached_prediction

        if pred.predicted_mode == TurnMode.ACT_TRANSITION:
            return TurnDecision(
                mode=TurnMode.ACT_TRANSITION,
                decision_layer=1,
                confidence=pred.confidence,
                focal_npcs=pred.focal_npcs,
                scene_mood=pred.scene_mood,
                tension_level=pred.tension_level,
                dialogue_phase=pred.dialogue_phase,
                phase_guidance=pred.phase_guidance,
                triggered_events=triggered_events,
                should_advance_reason="异步预判: 幕转换"
            )

        if pred.predicted_mode == TurnMode.PLOT_ADVANCE and pred.confidence >= 0.7:
            return TurnDecision(
                mode=TurnMode.PLOT_ADVANCE,
                decision_layer=1,
                confidence=pred.confidence,
                focal_npcs=pred.focal_npcs,
                scene_mood=pred.scene_mood,
                tension_level=pred.tension_level,
                dialogue_phase=pred.dialogue_phase,
                phase_guidance=pred.phase_guidance,
                triggered_events=triggered_events,
                should_advance_reason="异步预判: 剧情推进"
            )

        # 缓存预判为DIALOGUE，返回None让后续处理
        return None

    def _create_dialogue_decision(
        self,
        context: Dict[str, Any],
        triggered_events: List[GameEvent]
    ) -> TurnDecision:
        """创建DIALOGUE模式决策"""
        return TurnDecision(
            mode=TurnMode.DIALOGUE,
            decision_layer=2,
            confidence=0.8,
            focal_npcs=context.get("present_npcs", [])[:2],
            scene_mood=self.cached_prediction.scene_mood if self.cached_prediction.is_valid else "平静",
            tension_level=context.get("urgency", 0.3),
            dialogue_phase=self.dialogue_phase,
            phase_guidance=self._get_phase_guidance(),
            triggered_events=triggered_events
        )

    def _build_decision_context(
        self,
        player_input: str,
        game_context: Dict[str, Any],
        triggered_events: List[GameEvent]
    ) -> Dict[str, Any]:
        """构建决策上下文"""
        # 检查位置变化
        current_location = game_context.get("player_location")
        location_changed = False
        if current_location and self.last_location and current_location != self.last_location:
            location_changed = True

        # 计算紧迫度
        urgency = self._calculate_urgency()

        return {
            "player_input": player_input,
            "present_npcs": game_context.get("present_npcs", []),
            "current_location": current_location,
            "location_changed": location_changed,
            "progress": self.current_act.progress if self.current_act else 0.0,
            "turns_in_act": self.current_act.turns_in_act if self.current_act else 0,
            "max_turns": self.current_act.objective.max_turns if self.current_act else 15,
            "urgency": urgency,
            "dialogue_turns_since_plot": self.dialogue_turns_since_plot,
            "high_priority_events": [e for e in triggered_events if e.priority >= 8]
        }

    def _get_phase_guidance(self) -> str:
        """获取当前对话阶段的引导"""
        if self.dialogue_phase == DialoguePhase.OPENING:
            return "开场阶段：建立情境，NPC可以稍显保留"
        elif self.dialogue_phase == DialoguePhase.RISING:
            return "发展阶段：深入话题，NPC可以展现更多性格"
        elif self.dialogue_phase == DialoguePhase.CLIMAX:
            return "高潮阶段：关键时刻，NPC情绪应该更强烈"
        else:
            return "收尾阶段：总结或暗示，为下一幕铺垫"

    # ============================================================
    # 异步预判
    # ============================================================

    async def async_predict_next_turn(self, turn_result: Dict[str, Any]):
        """
        异步预判下一回合（后台执行）

        Args:
            turn_result: 当前回合结果 {
                player_input, npc_reactions, mode_used, ...
            }
        """
        if not self.enable_async_predict:
            return

        try:
            # 构建预判prompt
            prompt = self._build_prediction_prompt(turn_result)

            # 异步调用LLM
            result = await asyncio.to_thread(self.llm.invoke, prompt)
            prediction = self._parse_prediction_result(result.content)

            # 更新缓存
            self.cached_prediction = prediction
            self.cached_prediction.is_valid = True

            logger.debug(f"🔮 异步预判完成: {prediction.predicted_mode.value}")

        except Exception as e:
            logger.warning(f"⚠️ 异步预判失败: {e}")
            self.cached_prediction.is_valid = False

    def _build_prediction_prompt(self, turn_result: Dict[str, Any]) -> str:
        """构建预判提示词"""
        act_info = ""
        if self.current_act:
            act_info = f"""
## 当前幕信息
- 幕名称: {self.current_act.act_name}
- 幕目标: {self.current_act.objective.description}
- 当前进度: {self.current_act.progress:.0%}
- 已进行回合: {self.current_act.turns_in_act}/{self.current_act.objective.max_turns}
- 紧迫度: {self._calculate_urgency():.0%}
"""

        npc_summary = ""
        npc_reactions = turn_result.get("npc_reactions", [])
        if npc_reactions:
            summaries = []
            for r in npc_reactions[:3]:  # 最多3个
                npc = r.get("npc")
                reaction = r.get("reaction", {})
                if npc:
                    summaries.append(f"- {npc.character_name}: {reaction.get('dialogue', '')[:50]}...")
            npc_summary = "\n".join(summaries)

        return f"""分析当前对话状态，预测下一回合应该如何处理。

{act_info}

## 玩家最后行动
{turn_result.get('player_input', '')}

## NPC反应摘要
{npc_summary}

## 连续对话轮数
{self.dialogue_turns_since_plot} 轮

请判断下一回合的处理模式，输出JSON格式：
{{
  "predicted_mode": "DIALOGUE" 或 "PLOT_ADVANCE" 或 "ACT_TRANSITION",
  "confidence": 0.0-1.0,
  "scene_mood": "平静/紧张/温馨/悬疑/激烈",
  "tension_level": 0.0-1.0,
  "dialogue_phase": "OPENING/RISING/CLIMAX/FALLING",
  "phase_guidance": "给NPC的简短提示",
  "focal_npcs": ["应该重点响应的NPC名称"]
}}

判断依据：
- 如果对话自然结束或玩家表达离开意向 → ACT_TRANSITION
- 如果需要剧情推进（累积多轮对话、关键选择、重要发现）→ PLOT_ADVANCE
- 如果是普通闲聊、日常互动 → DIALOGUE
"""

    def _parse_prediction_result(self, content: str) -> TurnPrediction:
        """解析预判结果"""
        import json
        import re

        prediction = TurnPrediction()

        try:
            # 尝试提取JSON
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                mode_str = data.get("predicted_mode", "DIALOGUE").upper()
                if mode_str == "ACT_TRANSITION":
                    prediction.predicted_mode = TurnMode.ACT_TRANSITION
                elif mode_str == "PLOT_ADVANCE":
                    prediction.predicted_mode = TurnMode.PLOT_ADVANCE
                else:
                    prediction.predicted_mode = TurnMode.DIALOGUE

                prediction.confidence = float(data.get("confidence", 0.5))
                prediction.scene_mood = data.get("scene_mood", "平静")
                prediction.tension_level = float(data.get("tension_level", 0.3))

                phase_str = data.get("dialogue_phase", "OPENING").upper()
                if phase_str == "RISING":
                    prediction.dialogue_phase = DialoguePhase.RISING
                elif phase_str == "CLIMAX":
                    prediction.dialogue_phase = DialoguePhase.CLIMAX
                elif phase_str == "FALLING":
                    prediction.dialogue_phase = DialoguePhase.FALLING
                else:
                    prediction.dialogue_phase = DialoguePhase.OPENING

                prediction.phase_guidance = data.get("phase_guidance", "")
                prediction.focal_npcs = data.get("focal_npcs", [])

        except Exception as e:
            logger.debug(f"解析预判结果失败: {e}")

        return prediction

    # ============================================================
    # 幕管理（原ActDirector功能）
    # ============================================================

    def _create_default_act(self) -> Dict[str, Any]:
        """创建默认开放式幕（兼容方法，返回第一幕）"""
        return self._create_default_acts()[0]

    def _create_default_acts(self) -> List[Dict[str, Any]]:
        """
        创建默认多幕配置
        
        返回三幕结构：
        1. 探索与熟悉 - 让玩家熟悉世界和角色
        2. 发现端倪 - 引导玩家发现线索
        3. 抉择与行动 - 推动玩家做出关键决定
        """
        return [
            {
                "act_number": 1,
                "act_name": "探索与熟悉",
                "objective": {
                    "objective_id": "default_explore",
                    "description": "自由探索这个世界，与周围的人和事互动",
                    "internal_goal": "让玩家熟悉世界和角色，建立初步关系",
                    "completion_conditions": [
                        {"type": "turns_elapsed", "min_turns": 8},
                        {"type": "npc_interaction_count", "threshold": 3}
                    ],
                    "failure_conditions": [],
                    "max_turns": 25,
                    "urgency_curve": "linear",
                    "plot_guidance": "保持开放，响应玩家的探索行为。NPC可以主动分享信息、提出话题。"
                }
            },
            {
                "act_number": 2,
                "act_name": "发现端倪",
                "objective": {
                    "objective_id": "discover_clues",
                    "description": "深入了解这个世界的秘密",
                    "internal_goal": "引导玩家发现第一个重要线索或冲突",
                    "completion_conditions": [
                        {"type": "turns_elapsed", "min_turns": 6},
                        {"type": "npc_interaction_count", "threshold": 2}
                    ],
                    "failure_conditions": [],
                    "max_turns": 18,
                    "urgency_curve": "linear",
                    "plot_guidance": "通过NPC暗示或环境线索引导玩家。NPC应该开始透露一些深层信息。"
                }
            },
            {
                "act_number": 3,
                "act_name": "抉择与行动",
                "objective": {
                    "objective_id": "take_action",
                    "description": "是时候做出选择了",
                    "internal_goal": "推动玩家做出关键决定，剧情进入高潮",
                    "completion_conditions": [
                        {"type": "turns_elapsed", "min_turns": 5}
                    ],
                    "failure_conditions": [],
                    "max_turns": 15,
                    "urgency_curve": "climax",
                    "plot_guidance": "制造紧迫感，NPC主动推进剧情，给玩家施加选择压力。"
                }
            }
        ]

    def _initialize_first_act(self):
        """初始化第一幕"""
        if self.act_definitions:
            first_act_def = self.act_definitions[0]
            self.current_act = self._create_act_state(first_act_def)
            self._initialize_act_context()
            logger.info(f"🎬 开始第一幕: {self.current_act.act_name}")

    def _create_act_state(self, act_def: Dict[str, Any]) -> ActState:
        """从定义创建幕状态"""
        obj_def = act_def.get("objective", {})

        objective = ActObjective(
            objective_id=obj_def.get("objective_id", f"act_{act_def.get('act_number', 1)}"),
            description=obj_def.get("description", ""),
            internal_goal=obj_def.get("internal_goal", ""),
            completion_conditions=obj_def.get("completion_conditions", []),
            failure_conditions=obj_def.get("failure_conditions", []),
            max_turns=obj_def.get("max_turns", 15),
            urgency_curve=obj_def.get("urgency_curve", "linear"),
            plot_guidance=obj_def.get("plot_guidance", "")
        )

        return ActState(
            act_number=act_def.get("act_number", 1),
            act_name=act_def.get("act_name", f"第{act_def.get('act_number', 1)}幕"),
            objective=objective,
            turns_in_act=0,
            progress=0.0,
            completion_flags={},
            is_complete=False,
            outcome="ongoing",
            started_at=datetime.now().isoformat()
        )

    def _initialize_act_context(self):
        """初始化幕上下文"""
        if not self.current_act:
            return

        self.current_act_context = ActContext(
            act_number=self.current_act.act_number,
            act_name=self.current_act.act_name,
            act_theme=self.current_act.act_name,
            act_goal_for_player=self.current_act.objective.description,
            act_goal_internal=self.current_act.objective.internal_goal
        )

    def _calculate_urgency(self) -> float:
        """计算推进紧迫度"""
        if not self.current_act:
            return 0.5

        turns_ratio = self.current_act.turns_in_act / max(1, self.current_act.objective.max_turns)
        curve = self.current_act.objective.urgency_curve

        if curve == "linear":
            urgency = turns_ratio
        elif curve == "exponential":
            urgency = turns_ratio ** 0.5
        elif curve == "climax":
            if turns_ratio < 0.7:
                urgency = turns_ratio * 0.5
            else:
                urgency = 0.35 + (turns_ratio - 0.7) * 2.17
        else:
            urgency = turns_ratio

        # 如果进度落后，增加紧迫感
        if self.current_act.progress < turns_ratio * 0.8:
            urgency = min(1.0, urgency + 0.2)

        return min(1.0, max(0.0, urgency))

    def evaluate_progress(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """评估当前幕目标进度"""
        if not self.current_act:
            return self._empty_progress()

        # 更新追踪状态
        self._update_tracking_state(game_state)

        # 检查完成条件
        completed, pending = self._check_conditions(
            self.current_act.objective.completion_conditions,
            game_state
        )

        # 计算进度
        total_conditions = len(self.current_act.objective.completion_conditions)
        if total_conditions > 0:
            progress = len(completed) / total_conditions
        else:
            progress = min(1.0, self.current_act.turns_in_act / max(1, self.current_act.objective.max_turns))

        self.current_act.progress = progress
        urgency = self._calculate_urgency()

        # 检查是否应该推进
        should_advance = self._should_advance_act(completed, game_state)

        # 生成Plot提示
        plot_hints = self._generate_plot_hints(pending, urgency)

        return {
            "progress": progress,
            "completed_conditions": completed,
            "pending_conditions": pending,
            "urgency_level": urgency,
            "should_advance": should_advance,
            "plot_hints": plot_hints,
            "turns_remaining": max(0, self.current_act.objective.max_turns - self.current_act.turns_in_act),
            "turns_in_act": self.current_act.turns_in_act,
            "act_number": self.current_act.act_number,
            "act_name": self.current_act.act_name
        }

    def _update_tracking_state(self, game_state: Dict[str, Any]):
        """更新内部追踪状态"""
        location = game_state.get("player_location")
        if location and location not in self.locations_visited:
            self.locations_visited.append(location)

        interactions = game_state.get("npc_interactions", [])
        for interaction in interactions:
            npc_id = interaction.get("npc_id")
            if npc_id:
                self.npc_interaction_count[npc_id] = self.npc_interaction_count.get(npc_id, 0) + 1

        events = game_state.get("triggered_events", [])
        for event in events:
            event_id = event.get("event_id") if isinstance(event, dict) else str(event)
            if event_id and event_id not in self.key_events_occurred:
                self.key_events_occurred.append(event_id)

    def _check_conditions(self, conditions: List[Dict], game_state: Dict[str, Any]) -> tuple:
        """检查条件列表"""
        completed = []
        pending = []

        for cond in conditions:
            cond_type = cond.get("type")

            if cond_type == "npc_interaction_count":
                threshold = cond.get("threshold", 1)
                total = sum(self.npc_interaction_count.values())
                if total >= threshold:
                    completed.append(cond)
                else:
                    pending.append(cond)

            elif cond_type == "specific_npc_interaction":
                npc_id = cond.get("npc_id")
                threshold = cond.get("threshold", 1)
                if self.npc_interaction_count.get(npc_id, 0) >= threshold:
                    completed.append(cond)
                else:
                    pending.append(cond)

            elif cond_type == "location_visited":
                required = cond.get("locations", [])
                if all(loc in self.locations_visited for loc in required):
                    completed.append(cond)
                else:
                    pending.append(cond)

            elif cond_type == "flag":
                flag_name = cond.get("flag")
                expected = cond.get("value", True)
                if self.game_flags.get(flag_name) == expected:
                    completed.append(cond)
                else:
                    pending.append(cond)

            elif cond_type == "event_occurred":
                event_id = cond.get("event_id")
                if event_id in self.key_events_occurred:
                    completed.append(cond)
                else:
                    pending.append(cond)

            elif cond_type == "turns_elapsed":
                min_turns = cond.get("min_turns", 1)
                if self.current_act and self.current_act.turns_in_act >= min_turns:
                    completed.append(cond)
                else:
                    pending.append(cond)
            else:
                pending.append(cond)

        return completed, pending

    def _should_advance_act(self, completed_conditions: List[Dict], game_state: Dict[str, Any]) -> bool:
        """判断是否应该推进到下一幕"""
        if not self.current_act:
            return False

        total = len(self.current_act.objective.completion_conditions)
        if total > 0 and len(completed_conditions) >= total:
            return True

        if self.current_act.turns_in_act >= self.current_act.objective.max_turns:
            return True

        failed, _ = self._check_conditions(
            self.current_act.objective.failure_conditions,
            game_state
        )
        if failed:
            return True

        return False

    def _generate_plot_hints(self, pending_conditions: List[Dict], urgency: float) -> List[str]:
        """生成给Plot的提示"""
        hints = []

        for cond in pending_conditions:
            cond_type = cond.get("type")
            if cond_type == "npc_interaction_count":
                threshold = cond.get("threshold", 1)
                current = sum(self.npc_interaction_count.values())
                hints.append(f"引导玩家与更多NPC互动（当前{current}/{threshold}）")
            elif cond_type == "location_visited":
                required = cond.get("locations", [])
                unvisited = [loc for loc in required if loc not in self.locations_visited]
                if unvisited:
                    hints.append(f"可以暗示玩家探索: {', '.join(unvisited[:2])}")

        if urgency > 0.8:
            hints.append("剧情应该加速推进，制造关键转折")
        elif urgency > 0.6:
            hints.append("可以开始铺垫重要事件")

        if self.current_act and self.current_act.objective.plot_guidance:
            hints.append(f"引导: {self.current_act.objective.plot_guidance}")

        return hints

    def _empty_progress(self) -> Dict[str, Any]:
        """返回空的进度评估"""
        return {
            "progress": 0.0,
            "completed_conditions": [],
            "pending_conditions": [],
            "urgency_level": 0.5,
            "should_advance": False,
            "plot_hints": [],
            "turns_remaining": 999,
            "turns_in_act": 0,
            "act_number": 0,
            "act_name": "未初始化"
        }

    def advance_to_next_act(self, outcome: str = "success"):
        """推进到下一幕"""
        if not self.current_act:
            return

        # 标记当前幕完成
        self.current_act.is_complete = True
        self.current_act.outcome = outcome
        self.current_act.ended_at = datetime.now().isoformat()

        # 保存到历史
        self.act_history.append(self.current_act)

        logger.info(f"✅ 第{self.current_act.act_number}幕 [{self.current_act.act_name}] 完成: {outcome}")

        # 查找并切换到下一幕
        next_act_number = self.current_act.act_number + 1
        next_act_def = None

        for act_def in self.act_definitions:
            if act_def.get("act_number") == next_act_number:
                next_act_def = act_def
                break

        if not next_act_def:
            # 创建开放式幕（带有默认完成条件，确保紧迫度曲线正常工作）
            next_act_def = {
                "act_number": next_act_number,
                "act_name": f"第{next_act_number}幕 - 自由发展",
                "objective": {
                    "objective_id": f"act_{next_act_number}_open",
                    "description": "故事继续发展...",
                    "internal_goal": "基于之前的剧情自然发展",
                    "completion_conditions": [
                        {"type": "turns_elapsed", "min_turns": 8},
                        {"type": "npc_interaction_count", "threshold": 3}
                    ],
                    "max_turns": 20,
                    "urgency_curve": "linear",
                    "plot_guidance": "保持剧情连贯，响应玩家选择，在紧迫度上升时主动推进剧情"
                }
            }

        self.current_act = self._create_act_state(next_act_def)
        self._initialize_act_context()

        # 重置对话阶段
        self.dialogue_phase = DialoguePhase.OPENING
        self.phase_turn_count = 0
        self.dialogue_turns_since_plot = 0

        # 清除NPC幕剧本（下次需要重新生成）
        self.npc_act_briefings.clear()

        logger.info(f"🎬 开始新的一幕: {self.current_act.act_name}")

    def increment_turn(self):
        """增加当前幕的回合计数"""
        if self.current_act:
            self.current_act.turns_in_act += 1
            self.current_turn += 1
            logger.debug(f"📍 第{self.current_act.act_number}幕 回合 {self.current_act.turns_in_act}")

    def get_plot_context(self) -> Dict[str, Any]:
        """获取供Plot使用的幕目标上下文"""
        if not self.current_act:
            return {
                "current_act": 0,
                "act_name": "未初始化",
                "objective": "",
                "objective_description": "",
                "progress": 0.0,
                "urgency": 0.5,
                "turns_in_act": 0,
                "turns_remaining": 999,
                "guidance": "",
                "plot_hints": []
            }

        urgency = self._calculate_urgency()

        return {
            "current_act": self.current_act.act_number,
            "act_name": self.current_act.act_name,
            "objective": self.current_act.objective.internal_goal,
            "objective_description": self.current_act.objective.description,
            "progress": self.current_act.progress,
            "urgency": urgency,
            "turns_in_act": self.current_act.turns_in_act,
            "turns_remaining": max(0, self.current_act.objective.max_turns - self.current_act.turns_in_act),
            "guidance": self.current_act.objective.plot_guidance,
            "plot_hints": self._generate_plot_hints([], urgency)
        }

    # ============================================================
    # 事件管理（原EventEngine功能）
    # ============================================================

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
                    conditions=[{"type": "narrative_condition", "text": trigger_condition}]
                ),
                priority=8 if rule.get("is_rigid") else 5,
                effects=[],
                plot_override=None,
                is_repeatable=True
            )
            events.append(event)

        return events

    def check_triggers(
        self,
        game_state: Dict[str, Any],
        current_time: str,
        turn_number: int
    ) -> List[GameEvent]:
        """检查所有事件的触发条件"""
        triggered = []

        # 更新冷却
        for event in self.event_definitions + self.dynamic_events:
            if event.cooldown_remaining > 0:
                event.cooldown_remaining -= 1

        # 检查所有事件
        for event in self.event_definitions + self.dynamic_events:
            if self._should_trigger_event(event, game_state, current_time, turn_number):
                triggered.append(event)
                event.has_triggered = True
                event.triggered_at_turn = turn_number

                if event.trigger.probability_cooldown > 0:
                    event.cooldown_remaining = event.trigger.probability_cooldown

                self.triggered_history.append({
                    "event_id": event.event_id,
                    "event_name": event.event_name,
                    "turn": turn_number,
                    "timestamp": datetime.now().isoformat()
                })

                logger.info(f"⚡ 事件触发: [{event.event_id}] {event.event_name} (优先级:{event.priority})")

        triggered.sort(key=lambda e: e.priority, reverse=True)
        return triggered

    def _should_trigger_event(
        self,
        event: GameEvent,
        game_state: Dict[str, Any],
        current_time: str,
        turn_number: int
    ) -> bool:
        """检查单个事件是否应该触发"""
        if event.has_triggered and not event.is_repeatable:
            return False

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
            return False

        return False

    def _check_time_trigger(self, trigger: EventTrigger, current_time: str, turn_number: int) -> bool:
        """检查时间触发"""
        if trigger.trigger_time:
            try:
                target = datetime.strptime(trigger.trigger_time, "%Y-%m-%d %H:%M")
                current = datetime.strptime(current_time, "%Y-%m-%d %H:%M")
                if current >= target:
                    return True
            except ValueError:
                pass

        if trigger.time_after_turns is not None:
            if turn_number >= trigger.time_after_turns:
                return True

        return False

    def _check_condition_trigger(self, trigger: EventTrigger, game_state: Dict[str, Any]) -> bool:
        """检查条件触发"""
        for cond in trigger.conditions:
            cond_type = cond.get("type")

            if cond_type == "flag":
                flag_name = cond.get("flag")
                expected = cond.get("value", True)
                if self.game_flags.get(flag_name) != expected:
                    return False

            elif cond_type == "npc_mood":
                npc_id = cond.get("npc_id")
                expected_mood = cond.get("mood")
                npc_states = game_state.get("npc_states", {})
                actual_mood = npc_states.get(npc_id, {}).get("mood")
                if actual_mood != expected_mood:
                    return False

            elif cond_type == "location":
                expected = cond.get("location")
                actual = game_state.get("player_location")
                if actual != expected:
                    return False

            elif cond_type == "turns_elapsed":
                min_turns = cond.get("min_turns", 0)
                if self.current_turn < min_turns:
                    return False

            elif cond_type == "narrative_condition":
                pass  # 叙事条件需要LLM判断，这里跳过

        return True

    def _check_probability_trigger(self, trigger: EventTrigger) -> bool:
        """检查概率触发"""
        if trigger.probability <= 0:
            return False
        return random.random() < trigger.probability

    def apply_event_effects(self, event: GameEvent, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """应用事件效果"""
        effects_applied = []

        for effect in event.effects:
            effect_type = effect.get("type")

            if effect_type == "set_flag":
                flag_name = effect.get("flag")
                value = effect.get("value", True)
                self.game_flags[flag_name] = value
                effects_applied.append(f"设置标记 {flag_name}={value}")

            elif effect_type == "trigger_act_transition":
                outcome = effect.get("outcome", "success")
                effects_applied.append(f"触发幕转换: {outcome}")

        return {
            "event_id": event.event_id,
            "effects_applied": effects_applied,
            "plot_override": event.plot_override,
            "npc_reactions": event.npc_reactions
        }

    def set_flag(self, flag_name: str, value: Any):
        """设置游戏标记"""
        self.game_flags[flag_name] = value
        logger.debug(f"🚩 设置标记: {flag_name} = {value}")

    def get_flag(self, flag_name: str, default: Any = None) -> Any:
        """获取游戏标记"""
        return self.game_flags.get(flag_name, default)

    # ============================================================
    # NPC幕级视野
    # ============================================================

    def get_npc_act_briefing(self, npc_id: str) -> Optional[NPCActBriefing]:
        """获取NPC的幕级指令"""
        return self.npc_act_briefings.get(npc_id)

    async def generate_npc_act_briefings(self, present_npcs: List[Dict[str, Any]]):
        """
        为在场NPC生成幕级指令（幕开始时调用）

        Args:
            present_npcs: 在场NPC列表 [{id, name, traits, ...}, ...]
        """
        if not self.current_act or not present_npcs:
            return

        logger.info(f"📝 为 {len(present_npcs)} 个NPC生成幕级指令...")

        for npc_data in present_npcs:
            npc_id = npc_data.get("id") or npc_data.get("character_id")
            npc_name = npc_data.get("name") or npc_data.get("character_name")

            if not npc_id:
                continue

            # 检查是否已有指令
            if npc_id in self.npc_act_briefings:
                continue

            try:
                briefing = await self._generate_single_npc_briefing(npc_id, npc_name, npc_data)
                self.npc_act_briefings[npc_id] = briefing
                logger.debug(f"   - {npc_name}: {briefing.role_in_act}")
            except Exception as e:
                logger.warning(f"⚠️ 生成NPC[{npc_name}]幕指令失败: {e}")
                # 使用默认指令
                self.npc_act_briefings[npc_id] = NPCActBriefing(
                    npc_id=npc_id,
                    npc_name=npc_name or "未知",
                    role_in_act="参与者"
                )

    async def _generate_single_npc_briefing(
        self,
        npc_id: str,
        npc_name: str,
        npc_data: Dict[str, Any]
    ) -> NPCActBriefing:
        """为单个NPC生成幕级指令"""
        prompt = f"""为NPC生成本幕的角色指令。

## 幕信息
- 幕名称: {self.current_act.act_name if self.current_act else '未知'}
- 幕目标: {self.current_act.objective.description if self.current_act else '自由探索'}
- 内部目标: {self.current_act.objective.internal_goal if self.current_act else ''}

## NPC信息
- 名称: {npc_name}
- 性格: {npc_data.get('traits', [])}
- 背景: {npc_data.get('background', '')}

请为这个NPC生成本幕的角色指令，输出JSON格式：
{{
  "role_in_act": "引导者/阻碍者/旁观者/参与者",
  "knowledge_scope": ["本幕NPC知道的事情"],
  "forbidden_knowledge": ["本幕NPC不能透露的事情"],
  "emotional_journey": "从XX到XX的情感变化",
  "key_lines": ["可能说的关键台词提示"]
}}
"""

        try:
            result = await asyncio.to_thread(self.llm.invoke, prompt)
            return self._parse_npc_briefing(npc_id, npc_name, result.content)
        except Exception:
            return NPCActBriefing(npc_id=npc_id, npc_name=npc_name)

    def _parse_npc_briefing(self, npc_id: str, npc_name: str, content: str) -> NPCActBriefing:
        """解析NPC幕级指令"""
        import json
        import re

        briefing = NPCActBriefing(npc_id=npc_id, npc_name=npc_name)

        try:
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                briefing.role_in_act = data.get("role_in_act", "参与者")
                briefing.knowledge_scope = data.get("knowledge_scope", [])
                briefing.forbidden_knowledge = data.get("forbidden_knowledge", [])
                briefing.emotional_journey = data.get("emotional_journey", "")
                briefing.key_lines = data.get("key_lines", [])
        except Exception:
            pass

        return briefing

    # ============================================================
    # 回合更新
    # ============================================================

    def on_turn_complete(self, mode_used: TurnMode, player_input: str, location: str):
        """回合完成时更新状态"""
        # 更新位置追踪
        self.last_location = location

        # 更新对话计数
        if mode_used == TurnMode.DIALOGUE:
            self.dialogue_turns_since_plot += 1
            self.phase_turn_count += 1

            # 更新对话阶段
            if self.phase_turn_count >= 3:
                self._advance_dialogue_phase()
        else:
            self.dialogue_turns_since_plot = 0
            self.phase_turn_count = 0

        # 增加回合计数
        self.increment_turn()

        # 使缓存预判失效
        self.cached_prediction.is_valid = False

    def _advance_dialogue_phase(self):
        """推进对话阶段"""
        if self.dialogue_phase == DialoguePhase.OPENING:
            self.dialogue_phase = DialoguePhase.RISING
        elif self.dialogue_phase == DialoguePhase.RISING:
            self.dialogue_phase = DialoguePhase.CLIMAX
        elif self.dialogue_phase == DialoguePhase.CLIMAX:
            self.dialogue_phase = DialoguePhase.FALLING

        self.phase_turn_count = 0
        logger.debug(f"📈 对话阶段推进: {self.dialogue_phase.value}")

    # ============================================================
    # 状态快照
    # ============================================================

    def get_state_snapshot(self) -> Dict[str, Any]:
        """获取状态快照（用于持久化）"""
        return {
            "current_act": {
                "act_number": self.current_act.act_number if self.current_act else 0,
                "act_name": self.current_act.act_name if self.current_act else "",
                "turns_in_act": self.current_act.turns_in_act if self.current_act else 0,
                "progress": self.current_act.progress if self.current_act else 0.0,
                "is_complete": self.current_act.is_complete if self.current_act else False,
                "outcome": self.current_act.outcome if self.current_act else ""
            },
            "act_history_count": len(self.act_history),
            "game_flags": dict(self.game_flags),
            "npc_interaction_count": dict(self.npc_interaction_count),
            "locations_visited": list(self.locations_visited),
            "key_events_occurred": list(self.key_events_occurred),
            "current_turn": self.current_turn,
            "dialogue_turns_since_plot": self.dialogue_turns_since_plot,
            "dialogue_phase": self.dialogue_phase.value,
            "triggered_events_count": len(self.triggered_history)
        }
