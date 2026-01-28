# Python 3.14 + langchain 兼容性补丁
import langchain
if not hasattr(langchain, 'verbose'):
    langchain.verbose = False
if not hasattr(langchain, 'debug'):
    langchain.debug = False
if not hasattr(langchain, 'llm_cache'):
    langchain.llm_cache = None

import asyncio
import uvicorn
from datetime import datetime
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Optional
import json

from game_engine import GameEngine
from api.schemas import GameInitRequest, GameStateResponse, TurnResponse, ActionRequest, NPCReaction, HistoryEntry
from api.screen_adapter import ScreenAdapter
from config.settings import settings
from initial_Illuminati import IlluminatiInitializer
from utils.history_store import HistoryStore
from utils.logger import setup_logger

app = FastAPI(title="AAA-StoryMaker API")
logger = setup_logger("ApiServer", "api_server.log")

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Game Instance (Single Session for Demo)
game_engine: Optional[GameEngine] = None
screen_adapter: Optional[ScreenAdapter] = None


def _get_history_store() -> Optional[HistoryStore]:
    if not game_engine or not game_engine.runtime_dir:
        return None
    return HistoryStore(game_engine.runtime_dir)


def _extract_narration(text: str) -> Optional[str]:
    if not text:
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if line.startswith(("🎭", "💭", "[", "\"", "─", "=")):
            continue
        return line
    return None

@app.get("/")
def read_root():
    return {"message": "Welcome to AAA-StoryMaker API"}

@app.get("/worlds")
def get_worlds():
    """List available worlds"""
    worlds_dir = settings.DATA_DIR / "worlds"
    if not worlds_dir.exists():
        return []
    
    worlds = []
    for world_dir in worlds_dir.iterdir():
        if world_dir.is_dir() and (world_dir / "world_setting.json").exists():
            worlds.append(world_dir.name)
    return worlds

@app.get("/world/{world_name}/runtimes")
def get_runtimes(world_name: str):
    """List available runtimes (saves) for a world"""
    runtime_dir = settings.DATA_DIR / "runtime"
    if not runtime_dir.exists():
        return []
    
    runtimes = []
    for rt_dir in runtime_dir.iterdir():
        if rt_dir.is_dir() and rt_dir.name.startswith(f"{world_name}_"):
            # Check validation
            if (rt_dir / "genesis.json").exists():
                # Get metadata
                init_time = rt_dir.stat().st_mtime
                # Try to read summary if exists
                summary = {}
                try:
                    with open(rt_dir / "init_summary.json", "r") as f:
                        summary = json.load(f)
                except:
                    pass
                    
                runtimes.append({
                    "id": rt_dir.name,
                    "name": summary.get("player_profile", {}).get("name", "Unknown Player"),
                    "initialized_at": datetime.fromtimestamp(init_time).isoformat(),
                    "turn": 0 # TODO: read from state if possible
                })
    
    # Sort by newest first
    runtimes.sort(key=lambda x: x["initialized_at"], reverse=True)
    return runtimes

class GameInitRequest(BaseModel):
    world_name: str
    player_name: str = "Player"
    runtime_id: Optional[str] = None # If provided, load this save. If None, create new.

@app.post("/game/init", response_model=GameStateResponse)
async def init_game(request: GameInitRequest):
    """
    Initialize game:
    - If runtime_id is provided, load it.
    - If not, create a NEW runtime with player_name.
    """
    global game_engine, screen_adapter
    
    world_name = request.world_name
    runtime_dir = settings.DATA_DIR / "runtime"
    target_runtime = None
    
    is_new_runtime = request.runtime_id is None

    # Mode 1: Load existing
    if request.runtime_id:
        target_path = runtime_dir / request.runtime_id
        if target_path.exists() and (target_path / "genesis.json").exists():
            target_runtime = target_path
        else:
            raise HTTPException(status_code=404, detail="Save file not found")
    
    # Mode 2: Create New
    else:
        print(f"Creating new runtime for {world_name}...")
        try:
            # Run initializer in thread pool to avoid blocking
            initializer = IlluminatiInitializer(world_name, player_profile={"name": request.player_name})
            target_runtime = initializer.run()
            
            # Save genesis
            with open(target_runtime / "genesis.json", "w", encoding="utf-8") as f:
                json.dump(initializer.genesis_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create new game: {str(e)}")

    # Initialize Engine
    try:
        # Load engine
        game_engine = GameEngine(target_runtime / "genesis.json", async_mode=True)

        # Initialize Screen Adapter for visual generation
        screen_adapter = ScreenAdapter(game_engine)

        opening_text = None

        # Check if it's a fresh game (Turn 0)
        # Note: logic might differ if we loaded a save.
        # For now, if turn is 0, we assume it's start.
        if game_engine.os.turn_count == 0:
             opening_text = game_engine.start_game()

        status = game_engine.get_game_status()
        suggestions = game_engine.generate_action_suggestions()

        response = GameStateResponse(
            turn=status['turn'],
            location=str(status['location']),
            time=status['time'],
            text=opening_text or f"Loaded save: {target_runtime.name}",
            bgm_url=None,
            suggestions=suggestions
        )
        if opening_text and is_new_runtime:
            try:
                history_store = HistoryStore(target_runtime)
                if not history_store.has_entries():
                    history_store.append_entries([
                        history_store.build_entry(
                            turn=0,
                            seq=0,
                            role="system",
                            speaker_name="System",
                            content=opening_text,
                            meta={"event": "game_start"}
                        )
                    ])
            except Exception as e:
                logger.warning(f"Failed to persist opening history: {e}")
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/game/action", response_model=TurnResponse)
async def player_action(request: ActionRequest):
    global game_engine, screen_adapter
    if not game_engine:
        raise HTTPException(status_code=400, detail="Game not initialized")

    try:
        # Use Async method!
        result = await game_engine.process_turn_async(request.action)

        # 并行执行: suggestions 生成 + 视觉数据生成
        visual_task = None
        if screen_adapter and result.get("success"):
            visual_task = asyncio.create_task(
                screen_adapter.async_generate_visual_data(result)
            )

        suggestions = game_engine.generate_action_suggestions()

        # 等待视觉数据（100秒超时，LLM调用可能较慢）
        visual_data = None
        if visual_task:
            try:
                visual_data = await asyncio.wait_for(visual_task, timeout=100.0)
            except asyncio.TimeoutError:
                print("⚠️ 视觉数据生成超时，跳过")

        # 构建 NPC 反应列表
        npc_reactions = []
        if result.get("npc_reactions"):
            for item in result["npc_reactions"]:
                npc = item["npc"]
                reaction = item["reaction"]
                npc_reactions.append(NPCReaction(
                    character_name=npc.character_name,
                    dialogue=reaction.get("dialogue"),
                    action=reaction.get("action"),
                    emotion=reaction.get("emotion")
                ))

        response = TurnResponse(
            success=result["success"],
            text=result["text"],
            script=result.get("script", {}),
            atmosphere=result.get("atmosphere"),
            npc_reactions=npc_reactions,
            suggestions=suggestions,
            error=result.get("error"),
            visual_data=visual_data
        )
        try:
            history_store = _get_history_store()
            if history_store and result.get("success"):
                history_store.append_turn(
                    turn_id=getattr(game_engine.os, "turn_count", None),
                    player_action=request.action,
                    npc_reactions=[
                        {
                            "character_name": r.character_name,
                            "dialogue": r.dialogue,
                            "action": r.action,
                            "emotion": r.emotion,
                        }
                        for r in npc_reactions
                    ],
                    narration=_extract_narration(result.get("text", "")),
                    meta={"mode": result.get("mode")}
                )
        except Exception as e:
            logger.warning(f"Failed to persist history: {e}")
        return response
    except Exception as e:
         return TurnResponse(success=False, text=str(e), script={}, error=str(e))

@app.get("/game/state")
def get_state():
    global game_engine
    if not game_engine:
         raise HTTPException(status_code=400, detail="Game not initialized")
    status = game_engine.get_game_status()
    # Note: Calling generate_action_suggestions here might be slow for polling
    # For now we skip it in polling or we accept the latency
    # suggestions = game_engine.generate_action_suggestions()
    
    return {
        "turn": status['turn'],
        "location": str(status['location']),
        "time": status['time'],
        # "suggestions": suggestions
    }


@app.get("/game/history", response_model=list[HistoryEntry])
def get_history(
    limit: int = Query(200, ge=1, le=1000),
    before_turn: Optional[int] = None
):
    history_store = _get_history_store()
    if not history_store:
        raise HTTPException(status_code=400, detail="Game not initialized")
    return history_store.list_entries(limit=limit, before_turn=before_turn)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
