"""
状态管理器：负责协调本地文件与SQLite存储。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .local_store import LocalStore
from .models import (
    AgentState,
    CharacterCardVersion,
    EventLog,
    GameSave,
    MemoryDiff,
    now_iso,
)
from .sqlite_store import SQLiteStore


class StateManager:
    """状态写入的统一入口。"""

    def __init__(
        self,
        game_id: str,
        game_name: str,
        genesis_path: str,
        base_dir: Path | str = Path("data/runtime"),
    ) -> None:
        self.game_id = game_id
        self.game_name = game_name
        self.genesis_path = genesis_path
        self.base_dir = Path(base_dir)
        self.local_store = LocalStore(self.base_dir)
        self.sqlite_store = SQLiteStore(self.base_dir / "state.db")

        self.game_save_record = GameSave.create(game_name=game_name, genesis_path=genesis_path)
        self.game_save_record.id = game_id  # 使用外部传入的ID
        self._persist_game_metadata()

    def _persist_game_metadata(self) -> None:
        payload = self.game_save_record.to_dict()
        self.local_store.save_game_metadata(self.game_id, payload)
        self.sqlite_store.insert_game_save(
            {
                "id": payload["id"],
                "game_name": payload["game_name"],
                "genesis_path": payload["genesis_path"],
                "current_turn": payload["current_turn"],
                "created_at": payload["timestamp"],
                "last_played_at": payload["last_played_at"],
                "is_synced": int(payload["is_synced"]),
            }
        )

    def record_agent_state(
        self,
        agent_type: str,
        turn_number: int,
        state_snapshot: Dict[str, Any],
    ) -> AgentState:
        record = AgentState.create(
            game_id=self.game_id,
            agent_type=agent_type,
            turn_number=turn_number,
            state_snapshot=state_snapshot,
        )
        payload = record.to_dict()
        self.local_store.save_agent_state(
            self.game_id,
            agent_type,
            turn_number,
            payload,
        )
        self.sqlite_store.insert_agent_state(
            {
                "id": payload["id"],
                "game_id": payload["game_id"],
                "agent_type": payload["agent_type"],
                "turn_number": payload["turn_number"],
                "state_snapshot": payload["state_snapshot"],
                "timestamp": payload["timestamp"],
                "is_synced": int(payload["is_synced"]),
            }
        )
        return record

    def record_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        agent_source: str,
        turn_number: int,
    ) -> EventLog:
        record = EventLog.create(
            game_id=self.game_id,
            turn_number=turn_number,
            event_type=event_type,
            event_data=event_data,
            agent_source=agent_source,
        )
        payload = record.to_dict()
        self.local_store.append_event(self.game_id, turn_number, payload)
        self.sqlite_store.insert_event_log(
            {
                "id": payload["id"],
                "game_id": payload["game_id"],
                "turn_number": payload["turn_number"],
                "event_type": payload["event_type"],
                "event_data": payload["event_data"],
                "agent_source": payload["agent_source"],
                "timestamp": payload["timestamp"],
                "is_synced": int(payload["is_synced"]),
            }
        )
        return record

    def record_character_card(
        self,
        character_id: str,
        version: int,
        card_data: Dict[str, Any],
        changes: Optional[Dict[str, Any]],
        changed_by: str,
    ) -> CharacterCardVersion:
        record = CharacterCardVersion.create(
            game_id=self.game_id,
            character_id=character_id,
            version=version,
            card_data=card_data,
            changes=changes,
            changed_by=changed_by,
        )
        payload = record.to_dict()
        self.local_store.save_character_card(
            self.game_id,
            character_id,
            version,
            payload,
        )
        self.sqlite_store.insert_character_card(
            {
                "id": payload["id"],
                "game_id": payload["game_id"],
                "character_id": payload["character_id"],
                "version": payload["version"],
                "card_data": payload["card_data"],
                "changes": payload["changes"],
                "changed_by": payload["changed_by"],
                "timestamp": payload["timestamp"],
                "is_synced": int(payload["is_synced"]),
            }
        )
        return record

    def record_memory_diff(
        self,
        agent_type: str,
        field: str,
        old_value: Any,
        new_value: Any,
        trigger: str,
    ) -> MemoryDiff:
        record = MemoryDiff.create(
            game_id=self.game_id,
            agent_type=agent_type,
            field=field,
            old_value=old_value,
            new_value=new_value,
            trigger=trigger,
        )
        payload = record.to_dict()
        self.sqlite_store.insert_memory_diff(
            {
                "id": payload["id"],
                "game_id": payload["game_id"],
                "agent_type": payload["agent_type"],
                "field": payload["field"],
                "old_value": payload["old_value"],
                "new_value": payload["new_value"],
                "trigger": payload["trigger"],
                "timestamp": payload["timestamp"],
                "is_synced": int(payload["is_synced"]),
            }
        )
        return record

    def update_turn(self, turn_number: int) -> None:
        """更新当前回合数并刷新元数据。"""
        self.game_save_record.current_turn = turn_number
        self.game_save_record.last_played_at = now_iso()
        payload = self.game_save_record.to_dict()
        self.local_store.save_game_metadata(self.game_id, payload)
        self.sqlite_store.update_game_turn(
            self.game_id,
            turn_number,
            payload["last_played_at"],
        )

    def close(self) -> None:
        self.sqlite_store.close()

