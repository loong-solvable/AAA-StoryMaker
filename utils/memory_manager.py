"""
长期记忆管理器 (Memory Manager)
负责跨幕记忆的摘要和存储，提升NPC记忆连续性
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger("MemoryManager", "memory_manager.log")


class MemoryManager:
    """
    长期记忆管理器

    核心功能：
    - 每幕结束时生成对话摘要
    - 存储角色间的重要互动
    - 提供跨幕记忆查询
    """

    def __init__(self, runtime_dir: Optional[Path] = None):
        """
        初始化记忆管理器

        Args:
            runtime_dir: 运行时目录，用于持久化存储
        """
        self.runtime_dir = runtime_dir
        self.memory_file = runtime_dir / "memory" / "long_term_memory.json" if runtime_dir else None

        # 内存中的记忆存储
        self.memories: Dict[str, List[Dict[str, Any]]] = {
            "scene_summaries": [],  # 场景摘要
            "character_interactions": {},  # 角色间互动记录
            "significant_events": [],  # 重要事件
            "player_choices": []  # 玩家重要选择
        }

        # 尝试从文件加载
        if self.memory_file and self.memory_file.exists():
            self._load_from_file()

        logger.info("✅ 长期记忆管理器初始化完成")

    def _load_from_file(self):
        """从文件加载记忆"""
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.memories.update(data)
            logger.info(f"📁 已加载 {len(self.memories.get('scene_summaries', []))} 条场景记忆")
        except Exception as e:
            logger.warning(f"⚠️ 加载记忆文件失败: {e}")

    def _save_to_file(self):
        """保存记忆到文件"""
        if not self.memory_file:
            return

        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.memories, f, ensure_ascii=False, indent=2)
            logger.debug("💾 记忆已保存到文件")
        except Exception as e:
            logger.warning(f"⚠️ 保存记忆文件失败: {e}")

    def record_scene_summary(
        self,
        scene_number: int,
        location: str,
        participants: List[str],
        key_events: List[str],
        emotional_shifts: Dict[str, str],
        player_action_summary: str
    ):
        """
        记录场景摘要

        Args:
            scene_number: 场景编号
            location: 场景地点
            participants: 参与角色
            key_events: 关键事件列表
            emotional_shifts: 情感变化 {角色ID: "从X变为Y"}
            player_action_summary: 玩家行为摘要
        """
        summary = {
            "scene_number": scene_number,
            "location": location,
            "participants": participants,
            "key_events": key_events,
            "emotional_shifts": emotional_shifts,
            "player_action": player_action_summary,
            "timestamp": datetime.now().isoformat()
        }

        self.memories["scene_summaries"].append(summary)

        # 只保留最近20个场景摘要
        if len(self.memories["scene_summaries"]) > 20:
            self.memories["scene_summaries"] = self.memories["scene_summaries"][-20:]

        self._save_to_file()
        logger.info(f"📝 记录场景 {scene_number} 摘要，关键事件: {len(key_events)}")

    def record_interaction(
        self,
        character_id: str,
        player_action: str,
        character_response: str,
        emotional_impact: float,
        is_significant: bool = False
    ):
        """
        记录角色与玩家的互动

        Args:
            character_id: 角色ID
            player_action: 玩家行为
            character_response: 角色回应
            emotional_impact: 情感影响 (-1到1)
            is_significant: 是否为重要互动
        """
        if character_id not in self.memories["character_interactions"]:
            self.memories["character_interactions"][character_id] = []

        interaction = {
            "player_action": player_action[:100],
            "response": character_response[:100],
            "emotional_impact": emotional_impact,
            "is_significant": is_significant,
            "timestamp": datetime.now().isoformat()
        }

        self.memories["character_interactions"][character_id].append(interaction)

        # 每个角色只保留最近10次互动
        if len(self.memories["character_interactions"][character_id]) > 10:
            self.memories["character_interactions"][character_id] = \
                self.memories["character_interactions"][character_id][-10:]

        if is_significant:
            self._save_to_file()

    def record_significant_event(
        self,
        event_description: str,
        participants: List[str],
        consequences: List[str]
    ):
        """
        记录重要事件

        Args:
            event_description: 事件描述
            participants: 参与者
            consequences: 后果/影响
        """
        event = {
            "description": event_description,
            "participants": participants,
            "consequences": consequences,
            "timestamp": datetime.now().isoformat()
        }

        self.memories["significant_events"].append(event)

        # 只保留最近15个重要事件
        if len(self.memories["significant_events"]) > 15:
            self.memories["significant_events"] = self.memories["significant_events"][-15:]

        self._save_to_file()
        logger.info(f"⭐ 记录重要事件: {event_description[:30]}...")

    def get_character_memory(self, character_id: str, limit: int = 5) -> str:
        """
        获取角色对玩家的记忆摘要

        Args:
            character_id: 角色ID
            limit: 返回条数

        Returns:
            格式化的记忆文本
        """
        interactions = self.memories["character_interactions"].get(character_id, [])

        if not interactions:
            return "（与玩家尚无显著互动历史）"

        recent = interactions[-limit:]
        lines = []

        for i, inter in enumerate(recent, 1):
            impact = inter.get("emotional_impact", 0)
            if impact > 0.3:
                impact_desc = "正面"
            elif impact < -0.3:
                impact_desc = "负面"
            else:
                impact_desc = "中性"

            lines.append(f"- 玩家曾{inter['player_action'][:30]}... (影响: {impact_desc})")

        return "\n".join(lines)

    def get_scene_context(self, limit: int = 3) -> str:
        """
        获取最近场景的上下文摘要

        Args:
            limit: 返回的场景数

        Returns:
            格式化的场景摘要
        """
        summaries = self.memories["scene_summaries"][-limit:]

        if not summaries:
            return "（这是故事的开始）"

        lines = []
        for s in summaries:
            events = ", ".join(s.get("key_events", [])[:2])
            lines.append(f"场景{s['scene_number']}@{s['location']}: {events}")

        return "\n".join(lines)

    def get_significant_events(self, limit: int = 3) -> List[Dict[str, Any]]:
        """获取最近的重要事件"""
        return self.memories["significant_events"][-limit:]

    def generate_auto_summary(
        self,
        dialogue_history: List[Dict[str, str]],
        scene_number: int,
        location: str
    ) -> Dict[str, Any]:
        """
        自动从对话历史生成场景摘要

        Args:
            dialogue_history: 对话历史
            scene_number: 场景编号
            location: 地点

        Returns:
            生成的摘要数据
        """
        if not dialogue_history:
            return {}

        # 提取参与者
        participants = list(set(d.get("speaker_name", d.get("speaker", "")) for d in dialogue_history))

        # 提取玩家行为
        player_actions = [
            d.get("content", "")[:50]
            for d in dialogue_history
            if d.get("speaker") == "user"
        ]
        player_summary = "; ".join(player_actions[-3:]) if player_actions else "观察和倾听"

        # 简单的关键事件提取（基于关键词）
        key_events = []
        event_keywords = ["发现", "揭露", "决定", "承诺", "拒绝", "同意", "帮助", "威胁"]
        for d in dialogue_history:
            content = d.get("content", "")
            for kw in event_keywords:
                if kw in content:
                    key_events.append(f"{d.get('speaker_name', '某人')}{kw}了某事")
                    break

        return {
            "scene_number": scene_number,
            "location": location,
            "participants": participants,
            "key_events": key_events[:3],
            "player_action": player_summary
        }
