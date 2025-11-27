"""
SQLite存储，用于在本地维护结构化的热数据。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict


class SQLiteStore:
    """封装与SQLite的交互。"""

    def __init__(self, db_path: Path | str = Path("data/runtime/state.db")) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cursor = self.conn.cursor()
        cursor.executescript(
            """
            PRAGMA journal_mode = WAL;
            PRAGMA synchronous = NORMAL;

            CREATE TABLE IF NOT EXISTS game_saves (
                id TEXT PRIMARY KEY,
                game_name TEXT,
                genesis_path TEXT,
                current_turn INTEGER,
                created_at TEXT,
                last_played_at TEXT,
                is_synced INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS agent_states (
                id TEXT PRIMARY KEY,
                game_id TEXT,
                agent_type TEXT,
                turn_number INTEGER,
                state_snapshot TEXT,
                timestamp TEXT,
                is_synced INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS character_cards (
                id TEXT PRIMARY KEY,
                game_id TEXT,
                character_id TEXT,
                version INTEGER,
                card_data TEXT,
                changes TEXT,
                changed_by TEXT,
                timestamp TEXT,
                is_synced INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS event_logs (
                id TEXT PRIMARY KEY,
                game_id TEXT,
                turn_number INTEGER,
                event_type TEXT,
                event_data TEXT,
                agent_source TEXT,
                timestamp TEXT,
                is_synced INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS memory_diffs (
                id TEXT PRIMARY KEY,
                game_id TEXT,
                agent_type TEXT,
                field TEXT,
                old_value TEXT,
                new_value TEXT,
                trigger TEXT,
                timestamp TEXT,
                is_synced INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS sync_queue (
                id TEXT PRIMARY KEY,
                table_name TEXT,
                record_id TEXT,
                sync_attempts INTEGER DEFAULT 0,
                last_attempt_at TEXT,
                error_message TEXT,
                status TEXT DEFAULT 'pending'
            );
            """
        )
        self.conn.commit()

    def _insert(self, table: str, payload: Dict[str, Any]) -> None:
        placeholders = ", ".join(["?"] * len(payload))
        columns = ", ".join(payload.keys())
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        values = []
        for value in payload.values():
            if isinstance(value, (dict, list)):
                values.append(json.dumps(value, ensure_ascii=False))
            else:
                values.append(value)
        self.conn.execute(sql, values)
        self.conn.commit()

    def insert_game_save(self, payload: Dict[str, Any]) -> None:
        self._insert("game_saves", payload)

    def insert_agent_state(self, payload: Dict[str, Any]) -> None:
        self._insert("agent_states", payload)

    def insert_character_card(self, payload: Dict[str, Any]) -> None:
        self._insert("character_cards", payload)

    def insert_event_log(self, payload: Dict[str, Any]) -> None:
        self._insert("event_logs", payload)

    def insert_memory_diff(self, payload: Dict[str, Any]) -> None:
        self._insert("memory_diffs", payload)

    def update_game_turn(self, game_id: str, turn_number: int, last_played_at: str) -> None:
        self.conn.execute(
            "UPDATE game_saves SET current_turn = ?, last_played_at = ?, is_synced = 0 WHERE id = ?",
            (turn_number, last_played_at, game_id),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

