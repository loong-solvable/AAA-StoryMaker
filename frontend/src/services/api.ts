import axios from 'axios';

// 支持环境变量配置API地址，默认localhost:8000
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface GameState {
  turn: number;
  location: string;
  time: string;
  text?: string;
  image_url?: string;
  bgm_url?: string;
  suggestions?: string[];
}

export interface NPCReaction {
  character_name: string;
  dialogue?: string;
  action?: string;
  emotion?: string;
  voice_url?: string;
}

// ========== 视觉渲染数据类型 ==========

export interface VisualEnvironment {
  location: string;
  lighting: string;
  weather: string;
  composition: string;
}

export interface CharacterInShot {
  name: string;
  visual_tags: string;
  pose: string;
  expression: string;
  dialogue: string;
  action: string;
  screen_position: string;
}

export interface MediaPrompts {
  image_gen_prompt: string;
  video_gen_script: string;
  negative_prompt: string;
}

export interface VisualRenderData {
  summary: string;
  environment: VisualEnvironment;
  characters_in_shot: CharacterInShot[];
  media_prompts: MediaPrompts;
}

// ========== 响应类型 ==========

export interface TurnResponse {
  success: boolean;
  text: string;
  script: any;
  atmosphere?: any;
  npc_reactions: NPCReaction[];
  suggestions: string[];
  error?: string;
  visual_data?: VisualRenderData;
}

export interface HistoryEntry {
  id: string;
  turn: number;
  seq: number;
  role: string;
  speaker_name: string;
  content: string;
  action?: string;
  emotion?: string;
  timestamp: string;
  meta?: Record<string, unknown>;
}

const api = axios.create({
  baseURL: API_URL,
});

export const gameApi = {
  getWorlds: async () => {
    const res = await api.get<string[]>('/worlds');
    return res.data;
  },

  getRuntimes: async (worldName: string) => {
    const res = await api.get<{id: string, name: string, initialized_at: string, turn: number}[]>(`/world/${worldName}/runtimes`);
    return res.data;
  },
  
  
  initGame: async (worldName: string, playerName: string, runtimeId?: string) => {
    const res = await api.post<GameState>('/game/init', { 
      world_name: worldName, 
      player_name: playerName,
      runtime_id: runtimeId 
    });
    return res.data;
  },
  
  sendAction: async (action: string) => {
    const res = await api.post<TurnResponse>('/game/action', { action });
    return res.data;
  },

  getState: async () => {
    const res = await api.get<GameState>('/game/state');
    return res.data;
  },

  getHistory: async (limit = 200, beforeTurn?: number) => {
    const params: Record<string, string | number> = { limit };
    if (beforeTurn !== undefined) {
      params.before_turn = beforeTurn;
    }
    const res = await api.get<HistoryEntry[]>('/game/history', { params });
    return res.data;
  }
};
