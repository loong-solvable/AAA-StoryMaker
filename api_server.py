# Python 3.14 + langchain 兼容性补丁
import langchain
if not hasattr(langchain, 'verbose'):
    langchain.verbose = False
if not hasattr(langchain, 'debug'):
    langchain.debug = False
if not hasattr(langchain, 'llm_cache'):
    langchain.llm_cache = None

import asyncio
import uuid
import uvicorn
from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Optional, Dict
from threading import Lock
import json

from game_engine import GameEngine
from api.schemas import GameInitRequest, GameStateResponse, TurnResponse, ActionRequest, NPCReaction, HistoryEntry
from api.screen_adapter import ScreenAdapter
from config.settings import settings
from initial_Illuminati import IlluminatiInitializer
from utils.history_store import HistoryStore
from utils.logger import setup_logger
from utils.progress_tracker import ProgressTracker

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


# ============================================================
# 会话管理器 - 支持多用户
# ============================================================

class GameSession:
    """单个游戏会话"""
    def __init__(self, session_id: str, engine: GameEngine, screen_adapter: ScreenAdapter, runtime_dir: Path):
        self.session_id = session_id
        self.engine = engine
        self.screen_adapter = screen_adapter
        self.runtime_dir = runtime_dir
        self.created_at = datetime.now()
        self.last_active = datetime.now()
    
    def touch(self):
        """更新最后活跃时间"""
        self.last_active = datetime.now()
    
    def is_expired(self, timeout_minutes: int = 60) -> bool:
        """检查会话是否过期"""
        return datetime.now() - self.last_active > timedelta(minutes=timeout_minutes)


class SessionManager:
    """
    会话管理器 - 管理多个游戏会话
    
    特性:
    - 支持多用户同时游戏
    - 自动清理过期会话
    - 线程安全
    """
    
    def __init__(self, max_sessions: int = 100, session_timeout_minutes: int = 60):
        self._sessions: Dict[str, GameSession] = {}
        self._lock = Lock()
        self.max_sessions = max_sessions
        self.session_timeout_minutes = session_timeout_minutes
    
    def create_session(self, engine: GameEngine, screen_adapter: ScreenAdapter, runtime_dir: Path) -> str:
        """创建新会话，返回会话ID"""
        with self._lock:
            # 清理过期会话
            self._cleanup_expired_sessions()
            
            # 检查会话数限制
            if len(self._sessions) >= self.max_sessions:
                # 删除最老的会话
                oldest_id = min(self._sessions.keys(), key=lambda k: self._sessions[k].last_active)
                del self._sessions[oldest_id]
                logger.warning(f"会话数达上限，删除最老会话: {oldest_id}")
            
            session_id = str(uuid.uuid4())[:8]
            self._sessions[session_id] = GameSession(session_id, engine, screen_adapter, runtime_dir)
            logger.info(f"创建新会话: {session_id}, 当前会话数: {len(self._sessions)}")
            return session_id
    
    def get_session(self, session_id: str) -> Optional[GameSession]:
        """获取会话"""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                if session.is_expired(self.session_timeout_minutes):
                    del self._sessions[session_id]
                    logger.info(f"会话已过期: {session_id}")
                    return None
                session.touch()
            return session
    
    def remove_session(self, session_id: str) -> bool:
        """删除会话"""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"删除会话: {session_id}")
                return True
            return False
    
    def _cleanup_expired_sessions(self):
        """清理过期会话（内部方法，需在锁内调用）"""
        expired = [sid for sid, s in self._sessions.items() if s.is_expired(self.session_timeout_minutes)]
        for sid in expired:
            del self._sessions[sid]
            logger.info(f"清理过期会话: {sid}")
    
    def get_stats(self) -> Dict:
        """获取会话统计"""
        with self._lock:
            return {
                "active_sessions": len(self._sessions),
                "max_sessions": self.max_sessions,
                "timeout_minutes": self.session_timeout_minutes
            }


# 全局会话管理器
session_manager = SessionManager()

# 兼容旧API：保留默认会话（用于无session_id的请求）
default_session_id: Optional[str] = None


def _get_history_store(session: Optional[GameSession] = None) -> Optional[HistoryStore]:
    """获取历史存储，支持会话或默认全局引擎"""
    if session:
        return HistoryStore(session.runtime_dir)
    # 兼容旧模式
    global default_session_id
    if default_session_id:
        default_session = session_manager.get_session(default_session_id)
        if default_session:
            return HistoryStore(default_session.runtime_dir)
    return None


def _get_session(session_id: Optional[str] = None) -> GameSession:
    """获取会话，支持显式ID或默认会话"""
    global default_session_id
    
    # 优先使用显式传入的 session_id
    if session_id:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
        return session
    
    # 回退到默认会话
    if default_session_id:
        session = session_manager.get_session(default_session_id)
        if session:
            return session
    
    raise HTTPException(status_code=400, detail="Game not initialized. Call /game/init first.")


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
                    
                # Read turn count from progress.json if available
                turn_count = 0
                try:
                    progress = ProgressTracker().load_progress(rt_dir)
                    if not progress.is_corrupted:
                        turn_count = progress.turn_count
                except Exception:
                    pass  # Fallback to 0 if progress cannot be read
                
                runtimes.append({
                    "id": rt_dir.name,
                    "name": summary.get("player_profile", {}).get("name", "Unknown Player"),
                    "initialized_at": datetime.fromtimestamp(init_time).isoformat(),
                    "turn": turn_count
                })
    
    # Sort by newest first
    runtimes.sort(key=lambda x: x["initialized_at"], reverse=True)
    return runtimes

class GameInitRequest(BaseModel):
    world_name: str
    player_name: str = "Player"
    runtime_id: Optional[str] = None  # If provided, load this save. If None, create new.


class GameInitResponse(GameStateResponse):
    """游戏初始化响应，包含会话ID"""
    session_id: str = ""


@app.post("/game/init", response_model=GameInitResponse)
async def init_game(request: GameInitRequest):
    """
    Initialize game:
    - If runtime_id is provided, load it.
    - If not, create a NEW runtime with player_name.
    
    Returns:
    - session_id: 会话ID，后续请求需要携带此ID
    """
    global default_session_id
    
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
        logger.info(f"Creating new runtime for {world_name}...")
        try:
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
        engine = GameEngine(target_runtime / "genesis.json", async_mode=True)

        # Initialize Screen Adapter for visual generation
        adapter = ScreenAdapter(engine)

        # 创建会话
        session_id = session_manager.create_session(engine, adapter, target_runtime)
        
        # 设置为默认会话（向后兼容）
        default_session_id = session_id

        opening_text = None

        # Check if it's a fresh game (Turn 0)
        if engine.os.turn_count == 0:
            opening_text = engine.start_game()

        status = engine.get_game_status()
        suggestions = engine.generate_action_suggestions()

        response = GameInitResponse(
            session_id=session_id,
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
        
        logger.info(f"Game initialized: session={session_id}, world={world_name}")
        return response
    except Exception as e:
        logger.error(f"Failed to initialize game: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ActionRequestWithSession(ActionRequest):
    """带会话ID的行动请求"""
    session_id: Optional[str] = None


@app.post("/game/action", response_model=TurnResponse)
async def player_action(request: ActionRequestWithSession):
    """
    处理玩家行动
    
    Args:
        request.action: 玩家行动文本
        request.session_id: 会话ID（可选，不提供则使用默认会话）
    """
    try:
        session = _get_session(request.session_id)
        engine = session.engine
        screen_adapter = session.screen_adapter

        # Use Async method!
        result = await engine.process_turn_async(request.action)

        # 并行执行: suggestions 生成 + 视觉数据生成
        visual_task = None
        if screen_adapter and result.get("success"):
            visual_task = asyncio.create_task(
                screen_adapter.async_generate_visual_data(result)
            )

        suggestions = engine.generate_action_suggestions()

        # 等待视觉数据（100秒超时，LLM调用可能较慢）
        visual_data = None
        if visual_task:
            try:
                visual_data = await asyncio.wait_for(visual_task, timeout=100.0)
            except asyncio.TimeoutError:
                logger.warning("⚠️ 视觉数据生成超时，跳过")

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
            history_store = _get_history_store(session)
            if history_store and result.get("success"):
                history_store.append_turn(
                    turn_id=getattr(engine.os, "turn_count", None),
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Action failed: {e}")
        return TurnResponse(success=False, text=str(e), script={}, error=str(e))

@app.get("/game/state")
def get_state(session_id: Optional[str] = Query(None, description="会话ID")):
    """
    获取游戏状态
    
    Args:
        session_id: 会话ID（可选，不提供则使用默认会话）
    """
    session = _get_session(session_id)
    status = session.engine.get_game_status()
    
    return {
        "turn": status['turn'],
        "location": str(status['location']),
        "time": status['time'],
        # 幕目标信息
        "act": status.get('act', {})
    }


@app.get("/game/history", response_model=list[HistoryEntry])
def get_history(
    session_id: Optional[str] = Query(None, description="会话ID"),
    limit: int = Query(200, ge=1, le=1000),
    before_turn: Optional[int] = None
):
    """
    获取游戏历史
    
    Args:
        session_id: 会话ID（可选，不提供则使用默认会话）
        limit: 返回条目数量限制
        before_turn: 只返回此回合之前的条目
    """
    session = _get_session(session_id)
    history_store = _get_history_store(session)
    if not history_store:
        raise HTTPException(status_code=400, detail="History store not available")
    return history_store.list_entries(limit=limit, before_turn=before_turn)


@app.get("/sessions/stats")
def get_sessions_stats():
    """获取会话统计信息"""
    return session_manager.get_stats()


@app.delete("/game/session/{session_id}")
def close_session(session_id: str):
    """关闭指定会话"""
    if session_manager.remove_session(session_id):
        return {"message": f"Session {session_id} closed"}
    raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
