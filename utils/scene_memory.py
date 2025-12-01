"""
场景记忆板管理模块

管理演员之间共享的对话记录（公屏）。
每一幕大剧本对应一个 scene_memory.json 文件，所有演员共用。
"""
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger("SceneMemory", "scene_memory.log")


class SceneMemory:
    """
    场景记忆板
    
    管理一幕戏中所有演员共享的对话记录。
    """
    
    def __init__(self, memory_dir: Path, turn_id: int = 1):
        """
        初始化场景记忆板
        
        Args:
            memory_dir: 记忆目录路径，如 data/runtime/xxx/npc/memory
            turn_id: 当前幕次ID
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.turn_id = turn_id
        self.memory_file = self.memory_dir / "scene_memory.json"
        
        # 初始化或加载记忆
        self._data = self._load_or_create()
        
        logger.info(f"📋 场景记忆板初始化: turn_id={turn_id}, 已有 {len(self._data.get('dialogue_log', []))} 条记录")
    
    def _load_or_create(self) -> Dict[str, Any]:
        """加载或创建记忆文件"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 检查是否是同一幕
                    if data.get("meta", {}).get("turn_id") == self.turn_id:
                        return data
                    else:
                        # 新的一幕，归档旧记忆
                        self._archive_memory(data)
            except Exception as e:
                logger.error(f"❌ 读取记忆文件失败: {e}")
        
        # 创建新的记忆结构
        return self._create_new_memory()
    
    def _create_new_memory(self) -> Dict[str, Any]:
        """创建新的记忆结构"""
        return {
            "meta": {
                "turn_id": self.turn_id,
                "scene_status": "ACTIVE",
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            },
            "dialogue_log": []
        }
    
    def _archive_memory(self, old_data: Dict[str, Any]):
        """归档旧的记忆"""
        old_turn = old_data.get("meta", {}).get("turn_id", 0)
        archive_file = self.memory_dir / f"scene_memory_turn_{old_turn}.json"
        
        with open(archive_file, "w", encoding="utf-8") as f:
            json.dump(old_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📦 归档旧记忆: {archive_file.name}")
    
    def _save(self):
        """保存记忆到文件"""
        self._data["meta"]["last_updated"] = datetime.now().isoformat()
        
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
    
    def get_next_order_id(self) -> int:
        """获取下一个行动序列号"""
        dialogue_log = self._data.get("dialogue_log", [])
        if not dialogue_log:
            return 1
        return max(entry.get("order_id", 0) for entry in dialogue_log) + 1
    
    def add_dialogue(
        self,
        speaker_id: str,
        speaker_name: str,
        content: str,
        action: str = "",
        emotion: str = "",
        addressing_target: str = "everyone",
        thought: str = ""
    ) -> int:
        """
        添加一条对话记录
        
        Args:
            speaker_id: 说话者ID
            speaker_name: 说话者名称
            content: 对话内容
            action: 动作描述
            emotion: 情绪状态
            addressing_target: 对话对象（角色ID、user或everyone）
            thought: 内心活动（可选，不会显示给其他角色）
        
        Returns:
            分配的 order_id
        """
        order_id = self.get_next_order_id()
        
        entry = {
            "order_id": order_id,
            "speaker_id": speaker_id,
            "speaker_name": speaker_name,
            "content": content,
            "action": action,
            "emotion": emotion,
            "addressing_target": addressing_target,
            "timestamp": datetime.now().isoformat()
        }
        
        # thought 是内心活动，不写入公屏（但可以保存到私有日志）
        
        self._data["dialogue_log"].append(entry)
        self._save()
        
        logger.info(f"📝 [{order_id}] {speaker_name} -> {addressing_target}: {content[:30]}...")
        return order_id
    
    def get_dialogue_log(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        获取对话记录
        
        Args:
            limit: 限制返回的条数（从最新开始）
        
        Returns:
            对话记录列表
        """
        log = self._data.get("dialogue_log", [])
        if limit:
            return log[-limit:]
        return log
    
    def get_dialogue_for_prompt(self, exclude_speaker_id: str = None, limit: int = 10) -> str:
        """
        获取用于提示词的对话历史格式
        
        Args:
            exclude_speaker_id: 排除的说话者ID（可选）
            limit: 限制条数
        
        Returns:
            格式化的对话历史字符串
        """
        log = self.get_dialogue_log(limit)
        
        if not log:
            return "（这是对话的开始）"
        
        lines = []
        for entry in log:
            speaker = entry.get("speaker_name", "未知")
            content = entry.get("content", "")
            action = entry.get("action", "")
            target = entry.get("addressing_target", "everyone")
            
            # 构建对话对象描述
            target_desc = ""
            if target and target != "everyone":
                if target == "user":
                    target_desc = "（对玩家）"
                else:
                    target_desc = f"（对{target}）"
            
            if action:
                lines.append(f"【{speaker}】{target_desc}（{action}）: {content}")
            else:
                lines.append(f"【{speaker}】{target_desc}: {content}")
        
        return "\n".join(lines)
    
    def get_last_dialogue(self) -> Optional[Dict[str, Any]]:
        """获取最后一条对话记录"""
        log = self._data.get("dialogue_log", [])
        if log:
            return log[-1]
        return None
    
    def get_last_addressing_target(self) -> Optional[str]:
        """获取最后一条对话的对话对象"""
        last = self.get_last_dialogue()
        if last:
            return last.get("addressing_target")
        return None
    
    def get_last_speaker(self) -> Optional[str]:
        """获取最后一个说话者的ID"""
        log = self._data.get("dialogue_log", [])
        if log:
            return log[-1].get("speaker_id")
        return None
    
    def get_scene_status(self) -> str:
        """获取场景状态"""
        return self._data.get("meta", {}).get("scene_status", "UNKNOWN")
    
    def set_scene_status(self, status: str):
        """
        设置场景状态
        
        Args:
            status: 状态，如 "ACTIVE", "FINISHED", "PAUSED"
        """
        self._data["meta"]["scene_status"] = status
        self._save()
        logger.info(f"📋 场景状态更新: {status}")
    
    def get_dialogue_count(self) -> int:
        """获取对话条数"""
        return len(self._data.get("dialogue_log", []))
    
    def clear(self):
        """清空当前场景记忆（开始新场景时使用）"""
        # 先归档
        if self._data.get("dialogue_log"):
            self._archive_memory(self._data)
        
        self._data = self._create_new_memory()
        self._save()
        logger.info("🗑️ 场景记忆已清空")
    
    def to_dict(self) -> Dict[str, Any]:
        """返回完整的记忆数据"""
        return self._data.copy()


# 便捷函数
def create_scene_memory(runtime_dir: Path, turn_id: int = 1) -> SceneMemory:
    """
    创建场景记忆板实例
    
    Args:
        runtime_dir: 运行时目录，如 data/runtime/江城市_20251128_183246
        turn_id: 当前幕次ID
    
    Returns:
        SceneMemory 实例
    """
    memory_dir = runtime_dir / "npc" / "memory"
    return SceneMemory(memory_dir, turn_id)

