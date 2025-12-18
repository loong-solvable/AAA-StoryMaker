import axios from 'axios';

const API_URL = 'http://localhost:8000';

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

export interface TurnResponse {
  success: boolean;
  text: string;
  script: any;
  atmosphere?: any;
  npc_reactions: NPCReaction[];
  suggestions: string[];
  error?: string;
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
  }
};
