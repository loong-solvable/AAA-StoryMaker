from __future__ import annotations

import json
from typing import Any, Iterator, List, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult


class MockChatLLM(BaseChatModel):
    """Deterministic offline ChatModel for tests/CI.

    Goal:
    - Never touches network
    - Always returns valid JSON for pipelines that expect JSON
    - Minimal heuristics based on prompt content
    """

    def _join_messages(self, messages: List[BaseMessage]) -> str:
        parts: List[str] = []
        for m in messages:
            content = getattr(m, "content", "")
            if isinstance(content, str):
                parts.append(content)
            else:
                parts.append(str(content))
        return "\n\n".join(parts)

    def _make_json_content(self, messages: List[BaseMessage]) -> str:
        text = self._join_messages(messages)

        # WS init (initial_Illuminati.init_world_state)
        if "初始化模式" in text and ("世界状态" in text or "world_state" in text):
            payload: dict[str, Any] = {
                "current_scene": {
                    "location_id": "loc_mock_001",
                    "location_name": "测试地点",
                    "time_of_day": "下午",
                    "description": "用于测试的初始场景。",
                },
                "weather": {"condition": "晴朗", "temperature": "22°C"},
                "characters_present": [
                    {
                        "id": "user",
                        "name": "玩家",
                        "mood": "期待",
                        "activity": "观察局势",
                        "appearance_note": "",
                    }
                ],
                "characters_absent": [],
                "relationship_matrix": {},
                "world_situation": {
                    "summary": "测试用世界形势摘要。",
                    "tension_level": "平静",
                    "key_developments": [],
                },
                "meta": {
                    "game_turn": 0,
                    "last_updated": "2000-01-01T00:00:00",
                    "total_elapsed_time": "0分钟",
                },
            }
            return json.dumps(payload, ensure_ascii=False)

        # Vibe init (initial_Illuminati.init_vibe_and_generate_atmosphere)
        if ("氛围" in text or "Vibe" in text) and ("sensory_details" in text or "mood_keywords" in text):
            payload = {
                "sensory_details": {
                    "visual": ["暖色灯光", "人影晃动"],
                    "auditory": ["低声交谈", "远处车流"],
                    "olfactory": ["淡淡咖啡香"],
                },
                "mood_keywords": ["神秘", "期待"],
                "atmosphere_description": "(mock) 空气里有咖啡香与隐约的紧张感，故事即将开始。",
            }
            return json.dumps(payload, ensure_ascii=False)

        # WS incremental update (agents/online/layer2/ws_agent.py)
        if "只返回**变化的部分**" in text and "time_delta_minutes" in text:
            payload = {
                "time_delta_minutes": 10,
                "npc_updates": [],
                "offscreen_events": [],
                "environment_changes": [],
            }
            return json.dumps(payload, ensure_ascii=False)

        # NPC agent output (prompts/online/npc_system.txt expects strict JSON)
        if "Output Format" in text and "addressing_target" in text:
            payload = {
                "thought": "(mock) 分析局势并生成回应。",
                "emotion": "平静",
                "action": "(mock) 轻微点头。",
                "content": "(mock) 我明白了。",
                "addressing_target": "user",
                "is_scene_finished": False,
            }
            return json.dumps(payload, ensure_ascii=False)

        # Fallback: always JSON to reduce parse failures
        return json.dumps({"content": "[mock]"}, ensure_ascii=False)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        content = self._make_json_content(messages)
        if stop:
            for s in stop:
                if s and s in content:
                    content = content.split(s)[0]
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        content = self._make_json_content(messages)
        chunk = ChatGenerationChunk(message=AIMessageChunk(content=content))
        if run_manager:
            run_manager.on_llm_new_token(content, chunk=chunk)
        yield chunk

    @property
    def _llm_type(self) -> str:
        return "mock-chat"
