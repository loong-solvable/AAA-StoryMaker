"""
通用 NPC Agent 与 NPC 管理器

本模块为运行时提供：
- `NPCAgent`: 基于角色卡和统一 Prompt 的通用 NPC 实现
- `NPCManager`: 管理所有在场 NPC 的状态与实例

注意：
- 旧版按角色生成的 `npc_001_*.py` 等文件主要用于历史测试；
  游戏主循环 (`game_engine.py`) 只依赖本模块提供的 `NPCManager`。
"""
from __future__ import annotations

import asyncio
import os
import weakref
from typing import Any, Dict, List, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
from utils.logger import setup_logger
from utils.llm_factory import get_llm
from utils.json_parser import parse_json_response

# 尝试导入记忆管理器（可选依赖）
try:
    from utils.memory_manager import MemoryManager
    HAS_MEMORY_MANAGER = True
except ImportError:
    HAS_MEMORY_MANAGER = False
    MemoryManager = None

logger = setup_logger("NPCManager", "npc_manager.log")

# 全局并发限制（环境变量 LLM_CONCURRENCY，默认 3）
_LLM_CONCURRENCY = int(os.getenv("LLM_CONCURRENCY", "3"))
# 以事件循环为粒度缓存 Semaphore，避免跨循环错误
_LLM_SEMAPHORES: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore]" = (
    weakref.WeakKeyDictionary()
)


def _get_semaphore() -> asyncio.Semaphore:
    """
    获取与当前事件循环绑定的 Semaphore。
    如果不存在，则为该事件循环创建一个新的实例。
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop:
        sem = _LLM_SEMAPHORES.get(loop)
        if sem is None:
            sem = asyncio.Semaphore(_LLM_CONCURRENCY)
            _LLM_SEMAPHORES[loop] = sem
        return sem

    # 没有运行中的事件循环（例如同步上下文提前调用），返回独立实例
    return asyncio.Semaphore(_LLM_CONCURRENCY)


class NPCAgent:
    """
    通用 NPC Agent

    基于角色档案 + 场景上下文 + 导演指令，调用 LLM 生成 NPC 的行动与对白。
    """

    # 类级 Prompt 缓存，避免每次实例化都读取磁盘
    _prompt_template_cache: Optional[str] = None

    def __init__(self, character_data: Dict[str, Any]):
        self.character_data = character_data
        self.character_id: str = character_data.get("id", "npc_unknown")
        self.character_name: str = character_data.get("name", self.character_id)

        # 动态状态
        self.current_location: str = ""
        self.current_activity: str = ""
        self.current_mood: str = "平静"

        # 运行态关系（避免污染 genesis 原始数据）
        self.runtime_relationships: Dict[str, Dict[str, Any]] = {}

        # 情感向量化：追踪情感演变历史
        self.emotional_state: Dict[str, Any] = {
            "current_mood": "平静",
            "mood_history": [],  # 最近5个情绪状态
            "attitude_toward_player": 0.5,  # -1(敌对) 到 1(亲密), 0.5为中立
            "trust_level": 0.3,  # 0到1的信任度
            "last_significant_interaction": None,  # 最近的重要互动
            "emotional_triggers": []  # 情感触发事件
        }

        # 最近对话历史（滑动窗口，扩展到30条支持跨幕记忆）
        self.dialogue_history: List[Dict[str, str]] = []

        # LLM 与 Prompt
        online_timeout = getattr(settings, "ONLINE_LLM_TIMEOUT", 90.0)
        online_retries = getattr(settings, "ONLINE_LLM_MAX_RETRIES", 1)
        self.llm = get_llm(
            temperature=0.8,
            timeout=online_timeout,
            max_retries=online_retries
        )
        self.prompt_template = self._load_prompt_template()

        logger.info(
            "🎭 初始化通用 NPC Agent: %s (%s)", self.character_name, self.character_id
        )

    # --------------------------------------------------------------------- #
    # Prompt 构建
    # --------------------------------------------------------------------- #

    def _load_prompt_template(self) -> str:
        """加载通用 NPC 系统 Prompt 模板（使用类级缓存）。"""
        if NPCAgent._prompt_template_cache is not None:
            return NPCAgent._prompt_template_cache
        
        prompt_file = settings.PROMPTS_DIR / "online" / "npc_system.txt"
        if not prompt_file.exists():
            raise FileNotFoundError(f"未找到 NPC 提示词文件: {prompt_file}")
        
        NPCAgent._prompt_template_cache = prompt_file.read_text(encoding="utf-8")
        logger.info("📝 NPC Prompt 模板已缓存（仅首次加载）")
        return NPCAgent._prompt_template_cache

    def _format_relationships(self) -> str:
        """将 relationship_matrix 转换为可读文本。"""
        base_matrix = self.character_data.get("relationship_matrix") or {}
        # 叠加运行态关系（不直接修改 genesis 数据）
        matrix = dict(base_matrix)
        for k, v in self.runtime_relationships.items():
            matrix[k] = v

        if not isinstance(matrix, dict) or not matrix:
            return "暂无特别显著的人际关系。"

        lines: List[str] = []
        for target_id, rel in matrix.items():
            address_as = rel.get("address_as", "")
            attitude = rel.get("attitude", "")
            desc_parts = []
            if address_as:
                desc_parts.append(f"称呼: {address_as}")
            if attitude:
                desc_parts.append(f"态度: {attitude}")
            desc = "；".join(desc_parts) if desc_parts else "关系未明"
            lines.append(f"- 对 {target_id}: {desc}")

        return "\n".join(lines) if lines else "暂无特别显著的人际关系。"

    def _format_voice_samples(self) -> str:
        samples = self.character_data.get("voice_samples") or []
        if not samples:
            return "（暂无典型台词样本）"
        return "\n".join(f"- 「{s}」" for s in samples[:5])

    def _format_emotional_context(self) -> str:
        """格式化情感状态，供Prompt使用"""
        state = self.emotional_state
        mood_history = state.get("mood_history", [])
        attitude = state.get("attitude_toward_player", 0.5)
        trust = state.get("trust_level", 0.3)
        last_interaction = state.get("last_significant_interaction")

        # 态度描述
        if attitude > 0.7:
            attitude_desc = "对玩家非常友好和亲近"
        elif attitude > 0.4:
            attitude_desc = "对玩家保持友善但有所保留"
        elif attitude > 0.0:
            attitude_desc = "对玩家态度中立，有些警惕"
        elif attitude > -0.4:
            attitude_desc = "对玩家有些不满或不信任"
        else:
            attitude_desc = "对玩家抱有敌意或深深的不信任"

        # 信任描述
        if trust > 0.7:
            trust_desc = "高度信任"
        elif trust > 0.4:
            trust_desc = "有一定信任"
        else:
            trust_desc = "尚未建立信任"

        lines = [f"当前情绪: {state.get('current_mood', '平静')}"]

        if mood_history:
            lines.append(f"情绪演变: {' → '.join(mood_history[-3:])}")

        lines.append(f"对玩家态度: {attitude_desc} (信任度: {trust_desc})")

        if last_interaction:
            lines.append(f"最近重要互动: {last_interaction}")

        return "\n".join(lines)

    def _format_dialogue_history(self, limit: int = 15) -> str:
        """格式化最近的对话，用于 Prompt。包含内心独白作为推理上下文。"""
        if not self.dialogue_history:
            return "（这是对话的开始）"

        recent = self.dialogue_history[-limit:]
        lines: List[str] = []
        for item in recent:
            speaker = item.get("speaker_name", item.get("speaker", "未知"))
            content = item.get("content", "")
            line = f"【{speaker}】: {content}"

            # 如果是自己之前的发言，添加当时的内心独白作为推理上下文
            if item.get("speaker") == self.character_id and item.get("thought"):
                line += f" [当时心理: {item['thought'][:40]}]"
            if item.get("emotion"):
                line += f" [情绪: {item['emotion']}]"

            lines.append(line)
        return "\n".join(lines)

    def _format_present_characters(self, scene_context: Optional[Dict[str, Any]] = None) -> str:
        """
        格式化在场角色列表
        
        Args:
            scene_context: 场景上下文，应包含 present_characters 字段
            
        Returns:
            格式化的在场角色列表字符串
        """
        if not scene_context:
            logger.warning(f"[{self.character_name}] 未接收到 scene_context，无法显示在场角色")
            return "（未读取到scene_context）"
        
        present_chars = scene_context.get("present_characters", [])
        if not present_chars:
            logger.warning(f"[{self.character_name}] scene_context 中缺少 present_characters")
            return "（未读取到从scene_context中解析出的present_characters）"
        
        # 格式化为清晰的列表
        lines = []
        for char in present_chars:
            if isinstance(char, dict):
                char_id = char.get("id", "")
                char_name = char.get("name", char_id)
                is_player = char.get("is_player", False)
                
                if is_player:
                    # 特别标记玩家，帮助 NPC 理解玩家身份
                    lines.append(f"- {char_id}: {char_name} (玩家角色) ← 当你需要对玩家说话时，请使用 \"{char_id}\" 作为 addressing_target")
                else:
                    lines.append(f"- {char_id}: {char_name}")
            else:
                # 兼容性处理：如果只是字符串ID
                lines.append(f"- {char}")
        
        return "\n".join(lines) if lines else "（在场角色列表为空）"

    def _build_prompt(
        self,
        player_input: str,
        scene_context: Optional[Dict[str, Any]],
        director_instruction: Optional[Dict[str, Any]],
    ) -> str:
        """
        基于角色档案 + 场景信息 + 导演指令组装完整系统 Prompt。
        """
        scene_context = scene_context or {}
        director_instruction = director_instruction or {}
        params = director_instruction.get("parameters", {}) or {}

        # 角色基础信息
        traits = self.character_data.get("traits", [])
        behavior_rules = self.character_data.get("behavior_rules", [])

        # 场景与任务信息
        location = scene_context.get("location", "未知地点")
        time_str = scene_context.get("time", "未知时间")
        mood = scene_context.get("mood", "平静")

        # 构建情感状态描述
        emotional_context = self._format_emotional_context()

        global_context = (
            f"当前时间：{time_str}；地点：{location}；氛围：{mood}。\n"
            f"玩家刚刚的行动/发言：{player_input}\n\n"
            f"【你的情感状态】\n{emotional_context}"
        )

        # 场景摘要可能来自多个地方：director_instruction、params或scene_context
        scene_summary = (
            director_instruction.get("description")
            or director_instruction.get("summary", "")
            or params.get("scene_summary", "")
            or scene_context.get("scene_summary", "")
        )

        role_in_scene = params.get("role_in_scene", "普通参与者")
        objective = params.get("objective", "与玩家进行自然对话，推进剧情。")
        emotional_arc = params.get("emotional_arc", "根据对话逐步变化，保持合理。")
        key_topics = params.get("key_topics", [])
        if isinstance(key_topics, list):
            key_topics_str = "、".join(str(t) for t in key_topics)
        else:
            key_topics_str = str(key_topics)
        outcome_direction = params.get("outcome_direction", "让本幕自然收束。")
        special_notes = params.get("special_notes", "") or "无特别注意事项。"
        
        # 根据紧迫度添加主动推进指令
        urgency = params.get("urgency", 0)
        if urgency > 0.8:
            special_notes += "\n⚠️ 【紧迫度极高】剧情即将迎来转折！请主动推进核心目标，不要让对话陷入闲聊。主动抛出关键话题或做出推动剧情的行动。"
        elif urgency > 0.6:
            special_notes += "\n💡 【紧迫度较高】请开始积极推进剧情，主动引导对话向目标方向发展。"
        elif urgency > 0.4:
            special_notes += "\n📌 【紧迫度中等】如果对话偏离目标，请适时引导回正轨。"

        filled = (
            self.prompt_template.replace("{npc_name}", self.character_name)
            .replace("{npc_id}", self.character_id)
            .replace("{traits}", "、".join(traits) if traits else "性格待在对话中展现")
            .replace(
                "{behavior_rules}",
                "；".join(behavior_rules) if behavior_rules else "行为规则由常识与世界观推断",
            )
            .replace(
                "{appearance}",
                self.character_data.get("current_appearance", "外貌细节由你自由发挥"),
            )
            .replace("{relationships}", self._format_relationships())
            .replace("{voice_samples}", self._format_voice_samples())
            .replace("{global_context}", global_context)
            .replace(
                "{scene_summary}",
                scene_summary or "一幕围绕当前地点与角色的日常剧情。",
            )
            .replace("{role_in_scene}", role_in_scene)
            .replace("{objective}", objective)
            .replace("{emotional_arc}", emotional_arc)
            .replace("{key_topics}", key_topics_str or "（无特定话题要求）")
            .replace("{outcome_direction}", outcome_direction)
            .replace("{special_notes}", special_notes)
            .replace("{dialogue_history}", self._format_dialogue_history())
            .replace("{present_characters}", self._format_present_characters(scene_context))
        )

        return filled

    # --------------------------------------------------------------------- #
    # 对话主入口
    # --------------------------------------------------------------------- #

    def react(
        self,
        player_input: str,
        scene_context: Optional[Dict[str, Any]] = None,
        director_instruction: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        对玩家输入做出反应。

        Args:
            player_input: 玩家此次输入/行动描述
            scene_context: 当前场景上下文（位置/时间/氛围等）
            director_instruction: Plot 为该 NPC 给出的导演指令（可选）
        """
        logger.info("🎭 NPC[%s] 开始演绎一轮对话", self.character_id)

        # 先把玩家这一句记录到历史
        self._append_dialogue(
            speaker_id="user", speaker_name="玩家", content=player_input
        )

        system_prompt = self._build_prompt(
            player_input=player_input,
            scene_context=scene_context,
            director_instruction=director_instruction,
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content="请根据以上信息，以该角色的身份进行一次回应。"
                "严格按照提示中的 JSON 格式输出，不要添加额外说明。"
            ),
        ]

        try:
            response = self.llm.invoke(messages)
            content = getattr(response, "content", str(response))
            data = self._parse_response(content)
        except Exception as exc:  # noqa: BLE001
            logger.error("❌ NPC[%s] 调用 LLM 失败: %s", self.character_id, exc, exc_info=True)
            data = self._create_fallback_response()

        # 更新内部状态与历史
        dialogue_text = data.get("dialogue") or data.get("content") or ""
        if dialogue_text:
            self._append_dialogue(
                speaker_id=self.character_id,
                speaker_name=self.character_name,
                content=dialogue_text,
                thought=data.get("thought", ""),  # 存储内心独白供后续推理
                emotion=data.get("emotion", "")   # 存储情感状态
            )

        if data.get("emotion"):
            self.current_mood = data["emotion"]
            self._update_emotional_state(data, player_input)

        return data

    def _update_emotional_state(self, response_data: Dict[str, Any], player_input: str) -> None:
        """更新情感向量状态"""
        emotion = response_data.get("emotion", self.current_mood)

        # 更新情绪历史
        self.emotional_state["current_mood"] = emotion
        self.emotional_state["mood_history"].append(emotion)
        if len(self.emotional_state["mood_history"]) > 5:
            self.emotional_state["mood_history"] = self.emotional_state["mood_history"][-5:]

        # 分析玩家行为对态度的影响
        positive_keywords = ["帮助", "支持", "理解", "谢谢", "抱歉", "关心", "保护"]
        negative_keywords = ["威胁", "欺骗", "攻击", "无视", "嘲笑", "背叛"]

        attitude_delta = 0.0
        trust_delta = 0.0

        for kw in positive_keywords:
            if kw in player_input:
                attitude_delta += 0.05
                trust_delta += 0.03

        for kw in negative_keywords:
            if kw in player_input:
                attitude_delta -= 0.08
                trust_delta -= 0.05

        # 情感响应也会影响态度
        positive_emotions = ["感激", "信任", "高兴", "温暖", "希望", "欣慰"]
        negative_emotions = ["愤怒", "恐惧", "厌恶", "失望", "警惕"]

        if any(e in emotion for e in positive_emotions):
            attitude_delta += 0.02
            trust_delta += 0.02
        if any(e in emotion for e in negative_emotions):
            attitude_delta -= 0.02
            trust_delta -= 0.02

        # 更新态度和信任度（限制在合理范围）
        self.emotional_state["attitude_toward_player"] = max(-1.0, min(1.0,
            self.emotional_state["attitude_toward_player"] + attitude_delta))
        self.emotional_state["trust_level"] = max(0.0, min(1.0,
            self.emotional_state["trust_level"] + trust_delta))

        # 记录重要互动
        if abs(attitude_delta) > 0.03 or abs(trust_delta) > 0.02:
            self.emotional_state["last_significant_interaction"] = player_input[:50]
            self.emotional_state["emotional_triggers"].append({
                "input": player_input[:30],
                "emotion": emotion,
                "attitude_change": attitude_delta
            })
            if len(self.emotional_state["emotional_triggers"]) > 5:
                self.emotional_state["emotional_triggers"] = self.emotional_state["emotional_triggers"][-5:]

        # 更新关系矩阵中对玩家的态度
        self._update_relationship_with_player(attitude_delta)

    def _update_relationship_with_player(self, attitude_delta: float) -> None:
        """动态更新对玩家的关系描述"""
        if abs(attitude_delta) < 0.01:
            return

        # 获取或创建对玩家的关系条目（仅存储在运行态，不修改 genesis）
        rel_matrix = self.runtime_relationships
        if "user" not in rel_matrix:
            rel_matrix["user"] = {
                "address_as": "你",
                "attitude": "初次见面，保持观察"
            }

        attitude = self.emotional_state.get("attitude_toward_player", 0.5)
        trust = self.emotional_state.get("trust_level", 0.3)

        # 根据态度和信任度更新关系描述
        if attitude > 0.7 and trust > 0.6:
            rel_matrix["user"]["attitude"] = "非常信任和亲近，愿意分享秘密"
        elif attitude > 0.5 and trust > 0.4:
            rel_matrix["user"]["attitude"] = "友好且有一定信任，愿意合作"
        elif attitude > 0.3:
            rel_matrix["user"]["attitude"] = "保持友善但有所保留"
        elif attitude > 0.0:
            rel_matrix["user"]["attitude"] = "中立，保持警惕"
        elif attitude > -0.3:
            rel_matrix["user"]["attitude"] = "有些不满，保持距离"
        else:
            rel_matrix["user"]["attitude"] = "不信任，抱有敌意"

    async def async_react(
        self,
        player_input: str,
        scene_context: Optional[Dict[str, Any]] = None,
        director_instruction: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        异步版本的 react，使用线程池 + 并发限流。

        说明：
        - CustomChatZhipuAI 当前未实现 _agenerate，LangChain 的 ainvoke 会退化为线程池。
          这里显式使用 asyncio.to_thread，并通过全局 Semaphore 控制并发度，
          便于按需调整并发上限以避免 API 限流。
        """
        sem = _get_semaphore()
        async with sem:
            return await asyncio.to_thread(
                self.react,
                player_input,
                scene_context,
                director_instruction,
            )

    # --------------------------------------------------------------------- #
    # NPC 主动性方法 (Phase 3: 三合一RPG体验)
    # --------------------------------------------------------------------- #

    def decide_behavior(
        self,
        is_interaction_target: bool,
        scene_context: Optional[Dict[str, Any]] = None,
        other_npcs: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        决定本回合行为模式

        Args:
            is_interaction_target: 是否是玩家的交互目标
            scene_context: 场景上下文
            other_npcs: 其他在场NPC的ID列表

        Returns:
            {
                "mode": "respond"|"observe"|"autonomous"|"initiate",
                "priority": 1-10,
                "reason": "..."
            }
        """
        # 1. 如果是交互目标，必须响应
        if is_interaction_target:
            return {
                "mode": "respond",
                "priority": 10,
                "reason": f"{self.character_name}是玩家的交互目标"
            }

        # 2. 检查情感状态决定是否主动发起
        attitude = self.emotional_state.get("attitude_toward_player", 0.5)
        trust = self.emotional_state.get("trust_level", 0.3)

        # 降低主动发起门槛：中等好感度即可考虑主动发起
        if attitude > 0.5 and trust > 0.3:
            # 概率随态度增加：20%-40%
            import random
            initiative_chance = 0.2 + (attitude - 0.5) * 0.4
            if random.random() < initiative_chance:
                return {
                    "mode": "initiate",
                    "priority": 7,
                    "reason": f"{self.character_name}想主动推进对话"
                }
        
        # 即使态度中等，也有小概率主动（用于推进剧情）
        elif attitude > 0.3:
            import random
            if random.random() < 0.15:  # 15%概率
                return {
                    "mode": "initiate",
                    "priority": 5,
                    "reason": f"{self.character_name}有话想说"
                }

        # 3. 根据态度决定是否旁观
        if attitude > 0.4:
            return {
                "mode": "observe",
                "priority": 4,
                "reason": f"{self.character_name}关注场景中发生的事"
            }

        # 4. 低好感度可能执行自主行为
        if attitude < 0.3:
            return {
                "mode": "autonomous",
                "priority": 3,
                "reason": f"{self.character_name}对玩家不太关心，做自己的事"
            }

        # 5. 默认：旁观
        return {
            "mode": "observe",
            "priority": 2,
            "reason": f"{self.character_name}保持观察"
        }

    def observe_scene(
        self,
        player_input: str,
        scene_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        旁观模式 - 生成内心活动但不主动输出对话

        Returns:
            {
                "thought": "内心想法",
                "emotion": "情绪",
                "observation": "观察到什么",
                "should_interject": False,  # 是否应该插嘴
                "character_id": "...",
                "character_name": "..."
            }
        """
        # 简单的旁观响应，不调用LLM以节省token
        # 只记录NPC注意到了玩家的行为

        # 根据态度决定观察程度
        attitude = self.emotional_state.get("attitude_toward_player", 0.5)

        if attitude > 0.6:
            thought = f"{self.character_name}注意到玩家的动作，略带关心"
            should_interject = False  # 高好感但不随便插话
        elif attitude > 0.3:
            thought = f"{self.character_name}余光注意到玩家在做什么"
            should_interject = False
        else:
            thought = f"{self.character_name}对玩家的行为不太在意"
            should_interject = False

        return {
            "thought": thought,
            "emotion": self.current_mood,
            "observation": f"注意到: {player_input[:30]}...",
            "should_interject": should_interject,
            "character_id": self.character_id,
            "character_name": self.character_name,
            "mode": "observe"
        }

    def take_initiative(
        self,
        scene_context: Optional[Dict[str, Any]] = None,
        player_available: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        主动发起行动（不响应玩家输入，而是NPC自己的行为）

        Args:
            scene_context: 场景上下文
            player_available: 玩家是否可以被搭话

        Returns:
            主动行为数据，或None表示不主动行动
        """
        # 检查是否应该主动发起
        attitude = self.emotional_state.get("attitude_toward_player", 0.5)
        trust = self.emotional_state.get("trust_level", 0.3)

        # 构建主动发起的Prompt
        prompt = self._build_initiative_prompt(scene_context, player_available)

        try:
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content="请生成NPC的主动行为（对话或动作）")
            ]
            raw = self.llm.invoke(messages).content
            result = self._parse_response(raw)

            # 标记为主动发起
            result["mode"] = "initiate"
            result["is_initiative"] = True

            # 记录对话
            if result.get("dialogue"):
                self._append_dialogue(
                    self.character_id,
                    self.character_name,
                    result["dialogue"],
                    result.get("thought", ""),
                    result.get("emotion", "")
                )

            logger.info(f"💬 NPC[{self.character_name}] 主动发起: {result.get('dialogue', result.get('action', ''))[:50]}...")
            return result

        except Exception as e:
            logger.error(f"❌ NPC[{self.character_name}] 主动发起失败: {e}")
            return None

    def _build_initiative_prompt(
        self,
        scene_context: Optional[Dict[str, Any]],
        player_available: bool
    ) -> str:
        """构建主动发起的Prompt"""
        traits = self.character_data.get("traits") or []
        behavior_rules = self.character_data.get("behavior_rules") or []

        location = scene_context.get("location", "未知地点") if scene_context else "未知地点"
        mood = scene_context.get("mood", "平静") if scene_context else "平静"

        emotional_context = self._format_emotional_context()
        dialogue_history = self._format_dialogue_history(limit=5)

        prompt = f"""你是 {self.character_name}，一个有血有肉的角色。

# 你的性格特点
{', '.join(traits[:5]) if traits else '（未指定）'}

# 你的行为规则
{chr(10).join('- ' + r for r in behavior_rules[:3]) if behavior_rules else '（未指定）'}

# 当前情感状态
{emotional_context}

# 当前场景
- 地点: {location}
- 氛围: {mood}
- 玩家在场: {'是' if player_available else '否'}

# 最近对话
{dialogue_history if dialogue_history else '（无最近对话）'}

# 任务
你决定主动做点什么。可以是：
- 主动向玩家搭话
- 做一些符合你性格的动作
- 自言自语或思考

请输出JSON格式：
{{
    "thought": "你的内心想法",
    "emotion": "你的情绪",
    "dialogue": "你要说的话（如果你选择说话）",
    "action": "你的动作描述",
    "addressing_target": "user或everyone"
}}
"""
        return prompt

    async def async_observe_scene(
        self,
        player_input: str,
        scene_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """异步版本的旁观模式"""
        return self.observe_scene(player_input, scene_context)

    async def async_take_initiative(
        self,
        scene_context: Optional[Dict[str, Any]] = None,
        player_available: bool = True
    ) -> Optional[Dict[str, Any]]:
        """异步版本的主动发起"""
        sem = _get_semaphore()
        async with sem:
            return await asyncio.to_thread(
                self.take_initiative,
                scene_context,
                player_available
            )

    def _append_dialogue(
        self,
        speaker_id: str,
        speaker_name: str,
        content: str,
        thought: str = "",
        emotion: str = ""
    ) -> None:
        """记录一条对话，并维护滑动窗口。支持内心独白作为上下文。"""
        entry = {
            "speaker": speaker_id,
            "speaker_name": speaker_name,
            "content": content
        }
        # 仅NPC响应时存储内心独白（供后续推理使用，不展示给玩家）
        if thought:
            entry["thought"] = thought
        if emotion:
            entry["emotion"] = emotion

        self.dialogue_history.append(entry)
        # 保留最近 30 条（约 15 轮，支持跨幕记忆）
        if len(self.dialogue_history) > 30:
            self.dialogue_history = self.dialogue_history[-30:]

    # --------------------------------------------------------------------- #
    # JSON 解析与兜底
    # --------------------------------------------------------------------- #

    def _parse_response(self, raw: str) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON 响应，并做字段归一化。"""
        try:
            data = parse_json_response(raw) or {}
        except Exception as exc:  # noqa: BLE001
            logger.error("❌ NPC[%s] JSON解析失败: %s", self.character_id, exc, exc_info=True)
            return self._create_fallback_response(raw)

        # 兼容字段名：content / dialogue
        text = data.get("dialogue") or data.get("content") or ""
        data["dialogue"] = text
        data["content"] = text

        data.setdefault("thought", "")
        data.setdefault("emotion", self.current_mood)
        data.setdefault("action", "")
        data.setdefault("addressing_target", "everyone")
        data.setdefault("is_scene_finished", False)

        data["character_id"] = self.character_id
        data["character_name"] = self.character_name

        return data

    def _create_fallback_response(self, raw: str | None = None) -> Dict[str, Any]:
        """LLM 失败或解析失败时的兜底输出。"""
        preview = (raw or "").strip()
        if len(preview) > 100:
            preview = preview[:100] + "..."

        return {
            "character_id": self.character_id,
            "character_name": self.character_name,
            "thought": "（系统异常，采用兜底回复）",
            "emotion": self.current_mood,
            "action": "稍作思考，暂时没有大的动作",
            "dialogue": preview or "……",
            "content": preview or "……",
            "addressing_target": "everyone",
            "is_scene_finished": False,
        }

    # --------------------------------------------------------------------- #
    # 状态接口（供 GameEngine & 调试使用）
    # --------------------------------------------------------------------- #

    def update_state(
        self,
        location: Optional[str] = None,
        activity: Optional[str] = None,
        mood: Optional[str] = None,
    ) -> None:
        """更新 NPC 的位置 / 活动 / 心情。"""
        if location:
            self.current_location = location
        if activity:
            self.current_activity = activity
        if mood:
            self.current_mood = mood

    def get_state(self) -> Dict[str, Any]:
        """获取 NPC 当前状态快照。"""
        return {
            "id": self.character_id,
            "name": self.character_name,
            "location": self.current_location,
            "activity": self.current_activity,
            "mood": self.current_mood,
            "dialogue_count": len(self.dialogue_history),
            "emotional_state": {
                "attitude_toward_player": self.emotional_state.get("attitude_toward_player", 0.5),
                "trust_level": self.emotional_state.get("trust_level", 0.3),
                "mood_history": self.emotional_state.get("mood_history", [])[-3:],
            },
            "runtime_relationships": self.runtime_relationships,  # 动态关系矩阵
        }


class NPCManager:
    """
    NPC 管理器

    负责：
    - 基于 Genesis 数据按需创建 `NPCAgent` 实例
    - 接收 WS 输出的 `npc_updates`，同步到各 NPC
    - 提供统一的状态快照给 GameEngine
    """

    def __init__(self, genesis_data: Dict[str, Any]):
        self.genesis_data = genesis_data
        self.characters: List[Dict[str, Any]] = genesis_data.get("characters", [])
        self.npcs: Dict[str, NPCAgent] = {}

        logger.info("🧑‍🎭 NPCManager 初始化完成，角色总数: %d", len(self.characters))

    # ------------------------------------------------------------------ #
    # 工具方法
    # ------------------------------------------------------------------ #

    def _find_character(self, char_id: str) -> Optional[Dict[str, Any]]:
        for char in self.characters:
            if char.get("id") == char_id:
                return char
        return None

    # ------------------------------------------------------------------ #
    # 对外接口
    # ------------------------------------------------------------------ #

    def get_npc(self, char_id: str) -> Optional[NPCAgent]:
        """
        获取指定 ID 的 NPC 实例（不存在时按需创建）。
        """
        if not char_id or char_id == "user":
            return None

        if char_id in self.npcs:
            return self.npcs[char_id]

        char_data = self._find_character(char_id) or {
            "id": char_id,
            "name": char_id,
            "traits": [],
            "behavior_rules": [],
            "relationship_matrix": {},
            "current_appearance": "",
            "voice_samples": [],
        }

        npc = NPCAgent(char_data)
        self.npcs[char_id] = npc
        return npc

    def update_npc_states(self, npc_updates: List[Dict[str, Any]]) -> None:
        """
        根据 WS 返回的 npc_updates，更新所有 NPC 的状态。

        每个元素示例：
        {
            "npc_id": "npc_001",
            "current_location": "...",
            "current_activity": "...",
            "mood": "紧张"
        }
        """
        if not npc_updates:
            return

        for update in npc_updates:
            npc_id = update.get("npc_id")
            npc = self.get_npc(npc_id)
            if not npc:
                continue

            npc.update_state(
                location=update.get("current_location"),
                activity=update.get("current_activity"),
                mood=update.get("mood"),
            )

        logger.info("🔄 已应用 %d 条 NPC 状态更新", len(npc_updates))

    def get_state_snapshot(self) -> Dict[str, Any]:
        """
        返回所有已实例化 NPC 的状态快照。

        用于持久化和调试，不会强制实例化未使用的角色。
        """
        return {npc_id: npc.get_state() for npc_id, npc in self.npcs.items()}


__all__ = ["NPCAgent", "NPCManager"]
