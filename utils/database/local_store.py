"""
本地JSON文件存储，用于在写入数据库之前做备份。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class LocalStore:
    """负责将运行时数据写入 data/runtime/saves 目录。"""

    def __init__(self, base_dir: Path | str = Path("data/runtime")) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_game_dirs(self, game_id: str) -> Dict[str, Path]:
        game_root = self.base_dir / "saves" / game_id
        dirs = {
            "root": game_root,
            "agents": game_root / "agent_states",
            "characters": game_root / "character_cards",
            "events": game_root / "events",
        }
        for path in dirs.values():
            path.mkdir(parents=True, exist_ok=True)
        return dirs

    def save_game_metadata(self, game_id: str, metadata: Dict[str, Any]) -> Path:
        dirs = self._ensure_game_dirs(game_id)
        metadata_path = dirs["root"] / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return metadata_path

    def save_agent_state(
        self,
        game_id: str,
        agent_type: str,
        turn_number: int,
        payload: Dict[str, Any],
    ) -> Path:
        dirs = self._ensure_game_dirs(game_id)
        filename = f"{agent_type.lower()}_turn_{turn_number:04d}.json"
        file_path = dirs["agents"] / filename
        file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return file_path

    def append_event(
        self,
        game_id: str,
        turn_number: int,
        payload: Dict[str, Any],
    ) -> Path:
        dirs = self._ensure_game_dirs(game_id)
        filename = f"turn_{turn_number:04d}.jsonl"
        file_path = dirs["events"] / filename
        with file_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False))
            f.write("\n")
        return file_path

    def save_character_card(
        self,
        game_id: str,
        character_id: str,
        version: int,
        payload: Dict[str, Any],
    ) -> Path:
        dirs = self._ensure_game_dirs(game_id)
        filename = f"{character_id}_v{version:04d}.json"
        file_path = dirs["characters"] / filename
        file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return file_path

