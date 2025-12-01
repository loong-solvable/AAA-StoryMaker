"""
世界状态同步工具

提供在游戏运行时同步更新 ws/world_state.json 的功能。
使运行时目录中的状态文件与游戏进度保持同步。

使用方法：
    from utils.world_state_sync import WorldStateSync
    
    # 初始化
    sync = WorldStateSync(runtime_dir)
    
    # 更新状态
    sync.update_from_dict(new_state_dict)
    
    # 或增量更新
    sync.update_scene(location_id, location_name, time_of_day)
    sync.update_characters_present(characters_list)
    sync.increment_turn()
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from utils.logger import setup_logger

logger = setup_logger("WorldStateSync", "world_state_sync.log")


class WorldStateSync:
    """
    世界状态同步器
    
    负责在游戏运行时更新 ws/world_state.json 文件
    """
    
    def __init__(self, runtime_dir: Path):
        """
        初始化同步器
        
        Args:
            runtime_dir: 运行时目录路径，如 data/runtime/江城市_20251128_183246
        """
        self.runtime_dir = Path(runtime_dir)
        self.ws_file = self.runtime_dir / "ws" / "world_state.json"
        
        if not self.ws_file.exists():
            raise FileNotFoundError(f"world_state.json 不存在: {self.ws_file}")
        
        # 加载当前状态
        self._state = self._load_state()
        
        logger.info(f"✅ WorldStateSync 初始化完成: {self.ws_file}")
    
    def _load_state(self) -> Dict[str, Any]:
        """加载当前状态"""
        with open(self.ws_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _save_state(self):
        """保存状态到文件"""
        # 更新时间戳
        if "meta" not in self._state:
            self._state["meta"] = {}
        self._state["meta"]["last_updated"] = datetime.now().isoformat()
        
        # 写入文件
        with open(self.ws_file, "w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"💾 world_state.json 已更新")
    
    @property
    def state(self) -> Dict[str, Any]:
        """获取当前状态（只读）"""
        return self._state.copy()
    
    def update_from_dict(self, new_state: Dict[str, Any], merge: bool = True):
        """
        从字典更新状态
        
        Args:
            new_state: 新状态数据
            merge: 是否合并（True）还是完全替换（False）
        """
        if merge:
            self._deep_merge(self._state, new_state)
        else:
            self._state = new_state
        
        self._save_state()
        logger.info("✅ 世界状态已从字典更新")
    
    def _deep_merge(self, base: Dict, update: Dict):
        """深度合并字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    # ===========================================
    # 便捷更新方法
    # ===========================================
    
    def update_scene(
        self,
        location_id: str = None,
        location_name: str = None,
        time_of_day: str = None,
        description: str = None
    ):
        """
        更新当前场景
        
        Args:
            location_id: 地点ID
            location_name: 地点名称
            time_of_day: 时间段
            description: 场景描述
        """
        if "current_scene" not in self._state:
            self._state["current_scene"] = {}
        
        scene = self._state["current_scene"]
        if location_id is not None:
            scene["location_id"] = location_id
        if location_name is not None:
            scene["location_name"] = location_name
        if time_of_day is not None:
            scene["time_of_day"] = time_of_day
        if description is not None:
            scene["description"] = description
        
        self._save_state()
        logger.info(f"🎬 场景已更新: {scene.get('location_name', 'N/A')}")
    
    def update_weather(self, condition: str = None, temperature: str = None):
        """更新天气"""
        if "weather" not in self._state:
            self._state["weather"] = {}
        
        if condition is not None:
            self._state["weather"]["condition"] = condition
        if temperature is not None:
            self._state["weather"]["temperature"] = temperature
        
        self._save_state()
    
    def update_characters_present(self, characters: List[Dict[str, Any]]):
        """
        更新在场角色列表
        
        Args:
            characters: 角色列表，每个角色包含 id, name, mood, activity 等
        """
        self._state["characters_present"] = characters
        self._save_state()
        logger.info(f"👥 在场角色已更新: {len(characters)}人")
    
    def add_character_present(self, character: Dict[str, Any]):
        """添加一个在场角色"""
        if "characters_present" not in self._state:
            self._state["characters_present"] = []
        
        # 检查是否已存在
        char_id = character.get("id")
        existing_ids = [c.get("id") for c in self._state["characters_present"]]
        
        if char_id not in existing_ids:
            self._state["characters_present"].append(character)
            self._save_state()
            logger.info(f"➕ 添加在场角色: {character.get('name', char_id)}")
    
    def remove_character_present(self, character_id: str):
        """移除一个在场角色"""
        if "characters_present" not in self._state:
            return
        
        self._state["characters_present"] = [
            c for c in self._state["characters_present"]
            if c.get("id") != character_id
        ]
        self._save_state()
        logger.info(f"➖ 移除在场角色: {character_id}")
    
    def update_character_mood(self, character_id: str, mood: str, activity: str = None):
        """更新角色心情和活动"""
        if "characters_present" not in self._state:
            return
        
        for char in self._state["characters_present"]:
            if char.get("id") == character_id:
                char["mood"] = mood
                if activity:
                    char["activity"] = activity
                break
        
        self._save_state()
    
    def update_relationship(
        self,
        char_id_a: str,
        char_id_b: str,
        relation_type: str = None,
        attitude: str = None,
        recent_change: str = None
    ):
        """
        更新角色关系
        
        Args:
            char_id_a: 角色A的ID
            char_id_b: 角色B的ID
            relation_type: 关系类型
            attitude: 态度
            recent_change: 最近变化
        """
        if "relationship_matrix" not in self._state:
            self._state["relationship_matrix"] = {}
        
        matrix = self._state["relationship_matrix"]
        
        if char_id_a not in matrix:
            matrix[char_id_a] = {}
        
        if char_id_b not in matrix[char_id_a]:
            matrix[char_id_a][char_id_b] = {}
        
        rel = matrix[char_id_a][char_id_b]
        if relation_type is not None:
            rel["relation_type"] = relation_type
        if attitude is not None:
            rel["attitude"] = attitude
        if recent_change is not None:
            rel["recent_change"] = recent_change
        
        self._save_state()
        logger.info(f"💕 更新关系: {char_id_a} -> {char_id_b}")
    
    def update_world_situation(
        self,
        summary: str = None,
        tension_level: str = None,
        key_developments: List[str] = None
    ):
        """更新世界形势"""
        if "world_situation" not in self._state:
            self._state["world_situation"] = {}
        
        sit = self._state["world_situation"]
        if summary is not None:
            sit["summary"] = summary
        if tension_level is not None:
            sit["tension_level"] = tension_level
        if key_developments is not None:
            sit["key_developments"] = key_developments
        
        self._save_state()
        logger.info(f"🌍 世界形势已更新")
    
    def add_key_development(self, development: str):
        """添加关键进展"""
        if "world_situation" not in self._state:
            self._state["world_situation"] = {}
        if "key_developments" not in self._state["world_situation"]:
            self._state["world_situation"]["key_developments"] = []
        
        self._state["world_situation"]["key_developments"].append(development)
        self._save_state()
    
    def increment_turn(self):
        """递增游戏回合数"""
        if "meta" not in self._state:
            self._state["meta"] = {}
        
        current_turn = self._state["meta"].get("game_turn", 0)
        self._state["meta"]["game_turn"] = current_turn + 1
        
        self._save_state()
        logger.info(f"⏭️ 游戏回合: {current_turn + 1}")
        
        return current_turn + 1
    
    def update_elapsed_time(self, elapsed: str):
        """更新累计游戏时间"""
        if "meta" not in self._state:
            self._state["meta"] = {}
        
        self._state["meta"]["total_elapsed_time"] = elapsed
        self._save_state()
    
    def reload(self):
        """重新从文件加载状态"""
        self._state = self._load_state()
        logger.info("🔄 状态已从文件重新加载")


def sync_world_state(runtime_dir: Path, updates: Dict[str, Any]) -> bool:
    """
    便捷函数：同步更新世界状态
    
    Args:
        runtime_dir: 运行时目录
        updates: 要更新的内容
    
    Returns:
        是否成功
    """
    try:
        sync = WorldStateSync(runtime_dir)
        sync.update_from_dict(updates)
        return True
    except Exception as e:
        logger.error(f"❌ 同步世界状态失败: {e}")
        return False

