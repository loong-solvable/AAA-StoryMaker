from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from utils.logger import setup_logger

logger = setup_logger("HistoryStore", "history_store.log")


class HistoryStore:
    """Append-only history store for dialogue events."""

    def __init__(self, runtime_dir: Path):
        self.runtime_dir = Path(runtime_dir)
        self.history_dir = self.runtime_dir / "history"
        self.history_file = self.history_dir / "dialogue_history.jsonl"

    def _ensure_dir(self) -> None:
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def has_entries(self) -> bool:
        return self.history_file.exists() and self.history_file.stat().st_size > 0

    def _load_entries(self) -> List[Dict[str, Any]]:
        if not self.history_file.exists():
            return []

        entries: List[Dict[str, Any]] = []
        with self.history_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning("Skip invalid history line")
        return entries

    def _resolve_turn_id(self, turn_id: Optional[int]) -> int:
        last_turn = self.get_last_turn_id()
        if turn_id is None or turn_id <= last_turn:
            return last_turn + 1
        return turn_id

    def get_last_turn_id(self) -> int:
        entries = self._load_entries()
        if not entries:
            return 0
        return max(entry.get("turn", 0) for entry in entries)

    def list_entries(
        self,
        *,
        limit: int = 200,
        before_turn: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        entries = self._load_entries()
        if before_turn is not None:
            entries = [entry for entry in entries if entry.get("turn", 0) < before_turn]
        entries.sort(key=lambda entry: (entry.get("turn", 0), entry.get("seq", 0)))
        if limit:
            entries = entries[-limit:]
        return entries

    def append_entries(self, entries: Iterable[Dict[str, Any]]) -> None:
        items = list(entries)
        if not items:
            return
        self._ensure_dir()
        with self.history_file.open("a", encoding="utf-8") as handle:
            for entry in items:
                handle.write(json.dumps(entry, ensure_ascii=False))
                handle.write("\n")

    def build_entry(
        self,
        *,
        turn: int,
        seq: int,
        role: str,
        speaker_name: str,
        content: str,
        action: Optional[str] = None,
        emotion: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "id": uuid4().hex,
            "turn": turn,
            "seq": seq,
            "role": role,
            "speaker_name": speaker_name,
            "content": content,
            "action": action,
            "emotion": emotion,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if meta:
            payload["meta"] = meta
        return payload

    def append_turn(
        self,
        *,
        turn_id: Optional[int],
        player_action: str,
        npc_reactions: List[Dict[str, Any]],
        narration: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        resolved_turn = self._resolve_turn_id(turn_id)
        seq = 1
        entries: List[Dict[str, Any]] = []

        if narration:
            entries.append(
                self.build_entry(
                    turn=resolved_turn,
                    seq=seq,
                    role="narrator",
                    speaker_name="Narrator",
                    content=narration,
                    meta=meta,
                )
            )
            seq += 1

        if player_action:
            entries.append(
                self.build_entry(
                    turn=resolved_turn,
                    seq=seq,
                    role="player",
                    speaker_name="Player",
                    content=player_action,
                    meta=meta,
                )
            )
            seq += 1

        for reaction in npc_reactions:
            content = reaction.get("dialogue") or reaction.get("action") or ""
            if not content:
                continue
            entries.append(
                self.build_entry(
                    turn=resolved_turn,
                    seq=seq,
                    role="npc",
                    speaker_name=reaction.get("character_name", "NPC"),
                    content=content,
                    action=reaction.get("action"),
                    emotion=reaction.get("emotion"),
                    meta=meta,
                )
            )
            seq += 1

        self.append_entries(entries)
        return entries
