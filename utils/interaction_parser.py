"""
交互目标解析器 (Interaction Parser)
分析玩家输入，识别交互目标，智能判断哪些NPC应该响应
"""
import re
from typing import Dict, Any, List, Optional
from utils.logger import setup_logger

logger = setup_logger("InteractionParser", "interaction_parser.log")


def identify_interaction_target(
    player_input: str,
    present_characters: List[Dict[str, Any]],
    dialogue_history: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    分析玩家输入，识别交互目标

    Args:
        player_input: 玩家输入文本
        present_characters: 在场角色列表，每个角色包含 {"id": "npc_001", "name": "林晨", ...}
        dialogue_history: 对话历史（可选，用于上下文推断）

    Returns:
        {
            "target_type": "specific_npc"|"all_npcs"|"environment"|"self"|"unknown",
            "target_ids": ["npc_001"],  # 具体目标ID列表
            "target_names": ["林晨"],   # 目标名称列表
            "interaction_type": "dialogue"|"action"|"observation"|"internal",
            "confidence": 0.9,          # 置信度
            "reasoning": "..."          # 推理说明
        }
    """
    # 过滤掉玩家自己
    npc_chars = [c for c in present_characters if c.get("id") != "user"]

    if not npc_chars:
        return _create_result("environment", [], [], "observation", 1.0, "场景中没有NPC")

    # 构建角色名称到ID的映射
    name_to_id = {}
    id_to_name = {}
    for char in npc_chars:
        char_id = char.get("id", "")
        char_name = char.get("name", char_id)
        name_to_id[char_name] = char_id
        id_to_name[char_id] = char_name
        # 也添加别名/昵称支持
        if "nickname" in char:
            name_to_id[char["nickname"]] = char_id

    # 1. 检查直接提及的角色名
    mentioned_targets = _find_mentioned_characters(player_input, name_to_id)
    if mentioned_targets:
        target_names = [id_to_name.get(tid, tid) for tid in mentioned_targets]
        interaction_type = _infer_interaction_type(player_input)
        return _create_result(
            "specific_npc",
            mentioned_targets,
            target_names,
            interaction_type,
            0.95,
            f"玩家直接提到了角色: {', '.join(target_names)}"
        )

    # 2. 检查对话类关键词（暗示与NPC交互）
    dialogue_keywords = [
        "说", "问", "告诉", "回答", "聊", "交谈", "对话",
        "喊", "叫", "呼唤", "招呼", "搭话", "询问"
    ]
    if any(kw in player_input for kw in dialogue_keywords):
        # 有对话意图但没指定对象，尝试从上下文推断
        context_target = _infer_from_context(dialogue_history, npc_chars)
        if context_target:
            return _create_result(
                "specific_npc",
                [context_target["id"]],
                [context_target["name"]],
                "dialogue",
                0.7,
                f"根据上下文推断对话对象: {context_target['name']}"
            )
        # 无法推断，默认所有NPC
        return _create_result(
            "all_npcs",
            [c.get("id") for c in npc_chars],
            [c.get("name") for c in npc_chars],
            "dialogue",
            0.5,
            "有对话意图但未指定对象，所有NPC可能响应"
        )

    # 3. 检查环境交互关键词
    environment_keywords = [
        "看看", "观察", "环顾", "查看", "检查", "探索",
        "走", "移动", "离开", "进入", "打开", "关闭",
        "拿", "拾取", "放下", "使用"
    ]
    if any(kw in player_input for kw in environment_keywords):
        # 环境交互，NPC可能旁观
        return _create_result(
            "environment",
            [],
            [],
            "action",
            0.8,
            "玩家与环境交互，NPC可能旁观或不响应"
        )

    # 4. 检查内心活动关键词
    internal_keywords = [
        "想", "思考", "回忆", "琢磨", "考虑", "犹豫",
        "感觉", "觉得"
    ]
    if any(kw in player_input for kw in internal_keywords):
        return _create_result(
            "self",
            [],
            [],
            "internal",
            0.75,
            "玩家内心活动，NPC不应直接响应"
        )

    # 5. 检查代词
    pronoun_targets = _parse_pronouns(player_input, dialogue_history, npc_chars)
    if pronoun_targets:
        target_names = [id_to_name.get(tid, tid) for tid in pronoun_targets]
        return _create_result(
            "specific_npc",
            pronoun_targets,
            target_names,
            _infer_interaction_type(player_input),
            0.65,
            f"通过代词推断目标: {', '.join(target_names)}"
        )

    # 6. 默认情况：根据NPC数量决定
    if len(npc_chars) == 1:
        # 只有一个NPC，默认就是他
        single_npc = npc_chars[0]
        return _create_result(
            "specific_npc",
            [single_npc.get("id")],
            [single_npc.get("name")],
            _infer_interaction_type(player_input),
            0.6,
            f"场景只有一个NPC，默认目标: {single_npc.get('name')}"
        )
    else:
        # 多个NPC且无法确定，返回unknown让调用者决定
        return _create_result(
            "unknown",
            [c.get("id") for c in npc_chars],
            [c.get("name") for c in npc_chars],
            _infer_interaction_type(player_input),
            0.3,
            "无法确定交互目标，可能需要所有NPC响应或由Plot决定"
        )


def _find_mentioned_characters(
    text: str,
    name_to_id: Dict[str, str]
) -> List[str]:
    """查找文本中提到的角色"""
    mentioned = []
    for name, char_id in name_to_id.items():
        if name in text and char_id not in mentioned:
            mentioned.append(char_id)
    return mentioned


def _infer_interaction_type(text: str) -> str:
    """推断交互类型"""
    dialogue_keywords = ["说", "问", "告诉", "回答", "聊", "交谈", "对话", "喊", "叫"]
    action_keywords = ["走", "移动", "拿", "打", "推", "拉", "给", "递", "接"]
    observation_keywords = ["看", "观察", "检查", "注视", "盯着"]

    for kw in dialogue_keywords:
        if kw in text:
            return "dialogue"
    for kw in action_keywords:
        if kw in text:
            return "action"
    for kw in observation_keywords:
        if kw in text:
            return "observation"

    return "dialogue"  # 默认为对话


def _infer_from_context(
    dialogue_history: Optional[List[Dict]],
    npc_chars: List[Dict]
) -> Optional[Dict]:
    """从对话历史推断交互对象"""
    if not dialogue_history:
        return None

    # 查找最近一次NPC发言
    for entry in reversed(dialogue_history[-10:]):  # 只看最近10条
        speaker_id = entry.get("speaker_id", "")
        if speaker_id and speaker_id != "user":
            # 检查这个NPC是否在场
            for char in npc_chars:
                if char.get("id") == speaker_id:
                    return char
    return None


def _parse_pronouns(
    text: str,
    dialogue_history: Optional[List[Dict]],
    npc_chars: List[Dict]
) -> List[str]:
    """解析代词指代"""
    # 简单的代词检测
    male_pronouns = ["他", "他的"]
    female_pronouns = ["她", "她的"]
    plural_pronouns = ["他们", "她们", "它们"]

    targets = []

    # 检查是否有代词
    has_male = any(p in text for p in male_pronouns)
    has_female = any(p in text for p in female_pronouns)
    has_plural = any(p in text for p in plural_pronouns)

    if has_plural:
        # 复数代词，返回所有NPC
        return [c.get("id") for c in npc_chars]

    if has_male or has_female:
        # 尝试根据性别匹配
        gender_filter = "男" if has_male else "女"
        filtered = [c for c in npc_chars if c.get("gender", "") == gender_filter]

        if len(filtered) == 1:
            targets.append(filtered[0].get("id"))
        elif filtered:
            # 多个同性别NPC，尝试从上下文推断
            context_target = _infer_from_context(dialogue_history, filtered)
            if context_target:
                targets.append(context_target.get("id"))

    return targets


def _create_result(
    target_type: str,
    target_ids: List[str],
    target_names: List[str],
    interaction_type: str,
    confidence: float,
    reasoning: str
) -> Dict[str, Any]:
    """创建结果字典"""
    return {
        "target_type": target_type,
        "target_ids": target_ids,
        "target_names": target_names,
        "interaction_type": interaction_type,
        "confidence": confidence,
        "reasoning": reasoning
    }


def should_npc_respond(
    npc_id: str,
    npc_name: str,
    interaction_info: Dict[str, Any],
    npc_emotional_state: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    判断特定NPC是否应该响应

    Args:
        npc_id: NPC的ID
        npc_name: NPC的名称
        interaction_info: identify_interaction_target的返回结果
        npc_emotional_state: NPC的情感状态（可选）

    Returns:
        {
            "should_respond": True|False,
            "response_mode": "respond"|"observe"|"autonomous"|"ignore",
            "priority": 1-10,
            "reason": "..."
        }
    """
    target_type = interaction_info.get("target_type", "unknown")
    target_ids = interaction_info.get("target_ids", [])
    confidence = interaction_info.get("confidence", 0.5)

    # 1. 明确是交互目标
    if target_type == "specific_npc" and npc_id in target_ids:
        return {
            "should_respond": True,
            "response_mode": "respond",
            "priority": 10,
            "reason": f"{npc_name}是玩家的交互目标"
        }

    # 2. 所有NPC都应该响应
    if target_type == "all_npcs":
        return {
            "should_respond": True,
            "response_mode": "respond",
            "priority": 7,
            "reason": "玩家的行为面向所有在场角色"
        }

    # 3. 环境交互 - NPC可能旁观
    if target_type == "environment":
        # 根据NPC性格决定是否旁观
        if npc_emotional_state:
            attitude = npc_emotional_state.get("attitude_toward_player", 0.5)
            if attitude > 0.6:
                return {
                    "should_respond": True,
                    "response_mode": "observe",
                    "priority": 4,
                    "reason": f"{npc_name}对玩家友好，关注玩家行为"
                }
        return {
            "should_respond": False,
            "response_mode": "ignore",
            "priority": 2,
            "reason": f"{npc_name}不主动关注玩家的环境交互"
        }

    # 4. 玩家内心活动 - NPC不响应
    if target_type == "self":
        return {
            "should_respond": False,
            "response_mode": "ignore",
            "priority": 1,
            "reason": "玩家在思考，NPC无法感知"
        }

    # 5. 未知/不确定 - 交给自主决策
    if target_type == "unknown":
        # 可以考虑NPC的主动性
        if npc_emotional_state:
            attitude = npc_emotional_state.get("attitude_toward_player", 0.5)
            trust = npc_emotional_state.get("trust_level", 0.5)
            if attitude > 0.5 and trust > 0.4:
                return {
                    "should_respond": True,
                    "response_mode": "autonomous",
                    "priority": 5,
                    "reason": f"{npc_name}与玩家关系良好，可能主动互动"
                }
        return {
            "should_respond": True,
            "response_mode": "observe",
            "priority": 3,
            "reason": "情况不明确，NPC保持观察"
        }

    # 默认：不响应
    return {
        "should_respond": False,
        "response_mode": "ignore",
        "priority": 1,
        "reason": "不是交互目标"
    }
