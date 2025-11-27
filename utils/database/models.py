"""
数据模型定义，用于统一管理状态管理器与存储层之间的结构化数据。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

ISO_TIME_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"


def now_iso() -> str:
    """返回UTC时间的ISO字符串。"""
    return datetime.utcnow().strftime(ISO_TIME_FMT)


def generate_id() -> str:
    """统一的ID生成方法。"""
    return uuid4().hex


@dataclass
class BaseRecord:
    id: str
    timestamp: str
    is_synced: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


@dataclass
class GameSave(BaseRecord):
    game_name: str = ""
    genesis_path: str = ""
    current_turn: int = 0
    last_played_at: str = ""

    @classmethod
    def create(cls, game_name: str, genesis_path: str) -> "GameSave":
        return cls(
            id=generate_id(),
            timestamp=now_iso(),
            game_name=game_name,
            genesis_path=genesis_path,
            current_turn=0,
            last_played_at=now_iso(),
        )


@dataclass
class AgentState(BaseRecord):
    game_id: str = ""
    agent_type: str = ""
    turn_number: int = 0
    state_snapshot: Dict[str, Any] = None

    @classmethod
    def create(
        cls,
        game_id: str,
        agent_type: str,
        turn_number: int,
        state_snapshot: Dict[str, Any],
    ) -> "AgentState":
        return cls(
            id=generate_id(),
            timestamp=now_iso(),
            game_id=game_id,
            agent_type=agent_type,
            turn_number=turn_number,
            state_snapshot=state_snapshot,
        )


@dataclass
class CharacterCardVersion(BaseRecord):
    game_id: str = ""
    character_id: str = ""
    version: int = 1
    card_data: Dict[str, Any] = None
    changes: Optional[Dict[str, Any]] = None
    changed_by: str = "system"

    @classmethod
    def create(
        cls,
        game_id: str,
        character_id: str,
        version: int,
        card_data: Dict[str, Any],
        changes: Optional[Dict[str, Any]],
        changed_by: str,
    ) -> "CharacterCardVersion":
        return cls(
            id=generate_id(),
            timestamp=now_iso(),
            game_id=game_id,
            character_id=character_id,
            version=version,
            card_data=card_data,
            changes=changes,
            changed_by=changed_by,
        )


@dataclass
class EventLog(BaseRecord):
    game_id: str = ""
    turn_number: int = 0
    event_type: str = ""
    event_data: Dict[str, Any] = None
    agent_source: str = ""

    @classmethod
    def create(
        cls,
        game_id: str,
        turn_number: int,
        event_type: str,
        event_data: Dict[str, Any],
        agent_source: str,
    ) -> "EventLog":
        return cls(
            id=generate_id(),
            timestamp=now_iso(),
            game_id=game_id,
            turn_number=turn_number,
            event_type=event_type,
            event_data=event_data,
            agent_source=agent_source,
        )


@dataclass
class MemoryDiff(BaseRecord):
    game_id: str = ""
    agent_type: str = ""
    field: str = ""
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    trigger: str = ""

    @classmethod
    def create(
        cls,
        game_id: str,
        agent_type: str,
        field: str,
        old_value: Optional[Any],
        new_value: Optional[Any],
        trigger: str,
    ) -> "MemoryDiff":
        return cls(
            id=generate_id(),
            timestamp=now_iso(),
            game_id=game_id,
            agent_type=agent_type,
            field=field,
            old_value=old_value,
            new_value=new_value,
            trigger=trigger,
        )

