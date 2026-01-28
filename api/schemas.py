from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class GameInitRequest(BaseModel):
    world_name: str
    player_name: str = "Player"

class GameStateResponse(BaseModel):
    turn: int
    location: str
    time: str
    text: Optional[str] = None # Narrative text (Opening or Status)
    image_url: Optional[str] = None
    bgm_url: Optional[str] = None
    suggestions: List[str] = []

class NPCReaction(BaseModel):
    character_name: str
    dialogue: Optional[str] = None
    action: Optional[str] = None
    emotion: Optional[str] = None
    voice_url: Optional[str] = None

# ========== 视觉渲染数据模型 ==========

class VisualEnvironment(BaseModel):
    """环境视觉描述"""
    location: str = ""
    lighting: str = ""
    weather: str = ""
    composition: str = ""

class CharacterInShot(BaseModel):
    """镜头中的角色"""
    name: str
    visual_tags: str = ""
    pose: str = ""
    expression: str = ""
    dialogue: str = ""
    action: str = ""
    screen_position: str = "center"

class MediaPrompts(BaseModel):
    """AI生成媒体的提示词"""
    image_gen_prompt: str = ""
    video_gen_script: str = ""
    negative_prompt: str = "text, watermark, low quality, blurry, bad anatomy"

class VisualRenderData(BaseModel):
    """视觉渲染数据 - 供前端调用生图服务"""
    summary: str = ""
    environment: VisualEnvironment = VisualEnvironment()
    characters_in_shot: List[CharacterInShot] = []
    media_prompts: MediaPrompts = MediaPrompts()

# ========== 响应模型 ==========

class TurnResponse(BaseModel):
    success: bool
    text: str # Full narrative text
    script: Dict[str, Any]
    atmosphere: Optional[Dict[str, Any]] = None
    npc_reactions: List[NPCReaction] = []
    suggestions: List[str] = []
    error: Optional[str] = None
    visual_data: Optional[VisualRenderData] = None  # 视觉渲染数据

class ActionRequest(BaseModel):
    action: str
    audio_data: Optional[str] = None # Base64 encoded audio for future use


class HistoryEntry(BaseModel):
    id: str
    turn: int
    seq: int
    role: str
    speaker_name: str
    content: str
    action: Optional[str] = None
    emotion: Optional[str] = None
    timestamp: str
    meta: Optional[Dict[str, Any]] = None
