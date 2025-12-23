"""
幕导演 (Act Director)
管理幕目标和进度，让剧情有明确方向，多回合构成一幕
"""
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger("ActDirector", "act_director.log")


@dataclass
class ActObjective:
    """幕目标定义"""
    objective_id: str                           # 目标ID
    description: str                            # 目标描述（给玩家看的）
    internal_goal: str                          # 内部目标（给Plot用）
    completion_conditions: List[Dict] = field(default_factory=list)  # 完成条件
    failure_conditions: List[Dict] = field(default_factory=list)     # 失败条件
    max_turns: int = 15                         # 最大回合数
    urgency_curve: str = "linear"               # 紧迫感曲线: linear/exponential/climax
    plot_guidance: str = ""                     # 给Plot的引导建议


@dataclass
class ActState:
    """幕状态"""
    act_number: int                             # 当前幕编号 (从1开始)
    act_name: str                               # 幕名称
    objective: ActObjective                     # 当前目标
    turns_in_act: int = 0                       # 本幕已进行回合数
    progress: float = 0.0                       # 进度 0.0-1.0
    completion_flags: Dict[str, bool] = field(default_factory=dict)  # 条件完成标记
    is_complete: bool = False                   # 幕是否完成
    outcome: str = ""                           # "success"/"failure"/"timeout"/"ongoing"
    started_at: str = ""                        # 开始时间
    ended_at: str = ""                          # 结束时间


class ActDirector:
    """
    幕导演 - 管理幕目标和进度

    核心职责:
    1. 追踪当前幕的目标和进度
    2. 计算"推进压力"供Plot使用
    3. 判断何时切换到下一幕
    4. 支持运行时动态插入支线幕
    """

    def __init__(self, genesis_data: Dict[str, Any]):
        """
        初始化幕导演

        Args:
            genesis_data: Genesis世界数据，包含可选的 act_definitions
        """
        logger.info("🎭 初始化幕导演...")

        self.genesis_data = genesis_data

        # 加载幕定义（如果有）
        self.act_definitions: List[Dict] = genesis_data.get("act_definitions", [])

        # 如果没有预定义的幕，创建默认的开放式幕
        if not self.act_definitions:
            self.act_definitions = [self._create_default_act()]
            logger.info("📝 未找到预定义幕目标，使用默认开放式幕")

        # 当前幕状态
        self.current_act: Optional[ActState] = None

        # 历史记录
        self.act_history: List[ActState] = []

        # 游戏状态追踪（用于条件判断）
        self.game_flags: Dict[str, Any] = {}
        self.npc_interaction_count: Dict[str, int] = {}  # NPC交互次数
        self.locations_visited: List[str] = []           # 访问过的地点
        self.key_events_occurred: List[str] = []         # 发生的关键事件

        # 初始化第一幕
        self._initialize_first_act()

        logger.info(f"✅ 幕导演初始化完成")
        logger.info(f"   - 预定义幕数: {len(self.act_definitions)}")
        logger.info(f"   - 当前幕: {self.current_act.act_name if self.current_act else 'None'}")

    def _create_default_act(self) -> Dict[str, Any]:
        """创建默认的开放式幕（当没有预定义时使用）"""
        return {
            "act_number": 1,
            "act_name": "自由探索",
            "objective": {
                "objective_id": "default_explore",
                "description": "自由探索这个世界，与周围的人和事互动",
                "internal_goal": "让玩家熟悉世界和角色",
                "completion_conditions": [],  # 无硬性完成条件
                "failure_conditions": [],
                "max_turns": 999,  # 无限制
                "urgency_curve": "linear",
                "plot_guidance": "保持开放，响应玩家的探索行为"
            }
        }

    def _initialize_first_act(self):
        """初始化第一幕"""
        if self.act_definitions:
            first_act_def = self.act_definitions[0]
            self.current_act = self._create_act_state(first_act_def)
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

    def evaluate_progress(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估当前幕目标进度

        Args:
            game_state: 当前游戏状态，包含:
                - player_location: 玩家位置
                - present_characters: 在场角色
                - npc_interactions: NPC交互记录
                - triggered_events: 触发的事件
                - player_action: 玩家行动

        Returns:
            {
                "progress": 0.6,              # 总体进度
                "completed_conditions": [...], # 已完成的条件
                "pending_conditions": [...],   # 待完成的条件
                "urgency_level": 0.7,         # 推进压力 (0-1)
                "should_advance": False,       # 是否应该推进到下一幕
                "plot_hints": [...],          # 给Plot的提示
                "turns_remaining": 5          # 剩余回合数
            }
        """
        if not self.current_act:
            return self._empty_progress()

        # 更新内部追踪状态
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
            # 无硬性条件时，基于回合数计算进度
            progress = min(1.0, self.current_act.turns_in_act / max(1, self.current_act.objective.max_turns))

        self.current_act.progress = progress

        # 计算紧迫度
        urgency = self._calculate_urgency()

        # 检查是否应该推进
        should_advance = self._should_advance_act(completed, game_state)

        # 生成Plot提示
        plot_hints = self._generate_plot_hints(pending, urgency)

        # 更新完成标记
        for cond in completed:
            self.current_act.completion_flags[cond.get("type", "unknown")] = True

        result = {
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

        logger.debug(f"📊 幕进度评估: progress={progress:.2f}, urgency={urgency:.2f}")
        return result

    def _update_tracking_state(self, game_state: Dict[str, Any]):
        """更新内部追踪状态"""
        # 更新访问过的地点
        location = game_state.get("player_location")
        if location and location not in self.locations_visited:
            self.locations_visited.append(location)

        # 更新NPC交互计数
        interactions = game_state.get("npc_interactions", [])
        for interaction in interactions:
            npc_id = interaction.get("npc_id")
            if npc_id:
                self.npc_interaction_count[npc_id] = self.npc_interaction_count.get(npc_id, 0) + 1

        # 更新关键事件
        events = game_state.get("triggered_events", [])
        for event in events:
            event_id = event.get("event_id") if isinstance(event, dict) else str(event)
            if event_id and event_id not in self.key_events_occurred:
                self.key_events_occurred.append(event_id)

    def _check_conditions(
        self,
        conditions: List[Dict],
        game_state: Dict[str, Any]
    ) -> tuple:
        """
        检查条件列表

        Returns:
            (completed_conditions, pending_conditions)
        """
        completed = []
        pending = []

        for cond in conditions:
            cond_type = cond.get("type")

            if cond_type == "npc_interaction_count":
                # 检查NPC交互次数
                threshold = cond.get("threshold", 1)
                total_interactions = sum(self.npc_interaction_count.values())
                if total_interactions >= threshold:
                    completed.append(cond)
                else:
                    pending.append(cond)

            elif cond_type == "specific_npc_interaction":
                # 检查与特定NPC交互
                npc_id = cond.get("npc_id")
                threshold = cond.get("threshold", 1)
                if self.npc_interaction_count.get(npc_id, 0) >= threshold:
                    completed.append(cond)
                else:
                    pending.append(cond)

            elif cond_type == "location_visited":
                # 检查访问过的地点
                required_locations = cond.get("locations", [])
                if all(loc in self.locations_visited for loc in required_locations):
                    completed.append(cond)
                else:
                    pending.append(cond)

            elif cond_type == "flag":
                # 检查游戏标记
                flag_name = cond.get("flag")
                expected_value = cond.get("value", True)
                if self.game_flags.get(flag_name) == expected_value:
                    completed.append(cond)
                else:
                    pending.append(cond)

            elif cond_type == "event_occurred":
                # 检查事件是否发生
                event_id = cond.get("event_id")
                if event_id in self.key_events_occurred:
                    completed.append(cond)
                else:
                    pending.append(cond)

            elif cond_type == "turns_elapsed":
                # 检查回合数
                min_turns = cond.get("min_turns", 1)
                if self.current_act.turns_in_act >= min_turns:
                    completed.append(cond)
                else:
                    pending.append(cond)

            else:
                # 未知条件类型，标记为pending
                pending.append(cond)

        return completed, pending

    def _calculate_urgency(self) -> float:
        """
        计算推进紧迫度 (0-1)

        基于:
        - 已用回合数占比
        - 紧迫感曲线类型
        - 当前进度
        """
        if not self.current_act:
            return 0.5

        turns_ratio = self.current_act.turns_in_act / max(1, self.current_act.objective.max_turns)
        curve = self.current_act.objective.urgency_curve

        if curve == "linear":
            # 线性增长
            urgency = turns_ratio
        elif curve == "exponential":
            # 指数增长（后期压力更大）
            urgency = turns_ratio ** 0.5  # 平方根，前期增长快
        elif curve == "climax":
            # 高潮曲线（70%回合后急剧上升）
            if turns_ratio < 0.7:
                urgency = turns_ratio * 0.5
            else:
                urgency = 0.35 + (turns_ratio - 0.7) * 2.17  # 从0.35到1.0
        else:
            urgency = turns_ratio

        # 如果进度落后于回合进度，增加紧迫感
        if self.current_act.progress < turns_ratio * 0.8:
            urgency = min(1.0, urgency + 0.2)

        return min(1.0, max(0.0, urgency))

    def _should_advance_act(self, completed_conditions: List[Dict], game_state: Dict[str, Any]) -> bool:
        """判断是否应该推进到下一幕"""
        if not self.current_act:
            return False

        # 所有完成条件都满足
        total_conditions = len(self.current_act.objective.completion_conditions)
        if total_conditions > 0 and len(completed_conditions) >= total_conditions:
            return True

        # 超过最大回合数
        if self.current_act.turns_in_act >= self.current_act.objective.max_turns:
            return True

        # 检查失败条件
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

        # 基于待完成条件生成提示
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

            elif cond_type == "specific_npc_interaction":
                npc_id = cond.get("npc_id")
                hints.append(f"制造机会让玩家与 {npc_id} 互动")

        # 基于紧迫度生成提示
        if urgency > 0.8:
            hints.append("剧情应该加速推进，制造关键转折")
        elif urgency > 0.6:
            hints.append("可以开始铺垫重要事件")

        # 添加幕目标引导
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

    def check_act_transition(self) -> Optional[Dict[str, Any]]:
        """
        检查是否需要切换到下一幕

        Returns:
            None: 不需要切换
            Dict: 切换信息 {
                "new_act": ActState,
                "transition_type": "success"|"failure"|"timeout",
                "transition_event": "幕转换描述"
            }
        """
        if not self.current_act or not self.current_act.is_complete:
            return None

        # 查找下一幕定义
        next_act_number = self.current_act.act_number + 1
        next_act_def = None

        for act_def in self.act_definitions:
            if act_def.get("act_number") == next_act_number:
                next_act_def = act_def
                break

        if not next_act_def:
            # 没有下一幕，创建开放式幕
            next_act_def = {
                "act_number": next_act_number,
                "act_name": f"第{next_act_number}幕 - 自由发展",
                "objective": {
                    "objective_id": f"act_{next_act_number}_open",
                    "description": "故事继续发展...",
                    "internal_goal": "基于之前的剧情自然发展",
                    "completion_conditions": [],
                    "max_turns": 20,
                    "plot_guidance": "保持剧情连贯，响应玩家选择"
                }
            }

        # 创建新幕状态
        new_act = self._create_act_state(next_act_def)

        # 生成转换事件描述
        transition_event = self._generate_transition_event()

        return {
            "new_act": new_act,
            "transition_type": self.current_act.outcome,
            "transition_event": transition_event,
            "previous_act": self.current_act.act_name
        }

    def _generate_transition_event(self) -> str:
        """生成幕转换事件描述"""
        if not self.current_act:
            return "新的篇章开始..."

        outcome = self.current_act.outcome
        act_name = self.current_act.act_name

        if outcome == "success":
            return f"【{act_name}】圆满结束，新的篇章即将展开..."
        elif outcome == "failure":
            return f"【{act_name}】未能如愿，但故事仍在继续..."
        elif outcome == "timeout":
            return f"时光流逝，【{act_name}】落下帷幕，命运的齿轮继续转动..."
        else:
            return f"【{act_name}】告一段落..."

    def advance_to_next_act(self, outcome: str = "success"):
        """
        推进到下一幕

        Args:
            outcome: 当前幕的结果 "success"/"failure"/"timeout"
        """
        if not self.current_act:
            return

        # 标记当前幕完成
        self.current_act.is_complete = True
        self.current_act.outcome = outcome
        self.current_act.ended_at = datetime.now().isoformat()

        # 保存到历史
        self.act_history.append(self.current_act)

        logger.info(f"✅ 第{self.current_act.act_number}幕 [{self.current_act.act_name}] 完成: {outcome}")

        # 检查并切换到下一幕
        transition = self.check_act_transition()
        if transition:
            self.current_act = transition["new_act"]
            logger.info(f"🎬 开始新的一幕: {self.current_act.act_name}")

    def increment_turn(self):
        """增加当前幕的回合计数"""
        if self.current_act:
            self.current_act.turns_in_act += 1
            logger.debug(f"📍 第{self.current_act.act_number}幕 回合 {self.current_act.turns_in_act}")

    def record_npc_interaction(self, npc_id: str):
        """记录NPC交互"""
        self.npc_interaction_count[npc_id] = self.npc_interaction_count.get(npc_id, 0) + 1

    def set_flag(self, flag_name: str, value: Any):
        """设置游戏标记"""
        self.game_flags[flag_name] = value
        logger.debug(f"🚩 设置标记: {flag_name} = {value}")

    def add_dynamic_act(self, act_definition: Dict[str, Any], insert_next: bool = True):
        """
        动态添加新的幕定义（支持运行时插入支线）

        Args:
            act_definition: 幕定义
            insert_next: 是否作为下一幕插入（否则追加到末尾）
        """
        if insert_next and self.current_act:
            # 调整幕编号
            new_act_number = self.current_act.act_number + 1
            act_definition["act_number"] = new_act_number

            # 插入到当前幕之后
            insert_index = 0
            for i, act_def in enumerate(self.act_definitions):
                if act_def.get("act_number", 0) > self.current_act.act_number:
                    insert_index = i
                    break
                insert_index = i + 1

            # 后续幕编号+1
            for i in range(insert_index, len(self.act_definitions)):
                self.act_definitions[i]["act_number"] += 1

            self.act_definitions.insert(insert_index, act_definition)
        else:
            # 追加到末尾
            if self.act_definitions:
                max_num = max(a.get("act_number", 0) for a in self.act_definitions)
            else:
                max_num = 0
            act_definition["act_number"] = max_num + 1
            self.act_definitions.append(act_definition)

        logger.info(f"📝 动态添加幕: {act_definition.get('act_name', '未命名')}")

    def get_plot_context(self) -> Dict[str, Any]:
        """
        获取供Plot使用的幕目标上下文

        Returns:
            {
                "current_act": 1,
                "act_name": "初入江湖",
                "objective": "让玩家与3个NPC建立关系",
                "objective_description": "探索这个世界...",
                "progress": 0.6,
                "urgency": 0.7,
                "turns_in_act": 8,
                "turns_remaining": 7,
                "guidance": "...",
                "plot_hints": [...]
            }
        """
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

    def update_from_turn_result(
        self,
        player_action: str,
        npc_reactions: List[Dict],
        script: Dict[str, Any]
    ):
        """
        从回合结果更新状态

        Args:
            player_action: 玩家行动
            npc_reactions: NPC反应列表
            script: Plot生成的剧本
        """
        # 增加回合计数
        self.increment_turn()

        # 记录NPC交互
        for reaction in npc_reactions:
            npc = reaction.get("npc")
            if npc:
                npc_id = getattr(npc, "character_id", None)
                if npc_id:
                    self.record_npc_interaction(npc_id)

        # 检查剧本中的标记设置
        flags_to_set = script.get("flags_to_set", {})
        for flag_name, value in flags_to_set.items():
            self.set_flag(flag_name, value)

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
            "key_events_occurred": list(self.key_events_occurred)
        }
