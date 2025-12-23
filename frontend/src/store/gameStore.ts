import { create } from 'zustand';
import { gameApi, NPCReaction, VisualRenderData } from '../services/api';

interface GameStore {
  isStarted: boolean;
  currentTurn: number;
  location: string;
  time: string;
  lastText: string;
  npcReactions: NPCReaction[];
  isLoading: boolean;
  error: string | null;

  suggestions: string[];
  visualData: VisualRenderData | null;  // 视觉渲染数据

  initGame: (world: string, player: string, runtimeId?: string) => Promise<void>;
  sendAction: (action: string) => Promise<void>;
}

export const useGameStore = create<GameStore>((set) => ({
  isStarted: false,
  currentTurn: 0,
  location: "Unknown",
  time: "Day",
  lastText: "Welcome to the game.",
  npcReactions: [],
  suggestions: [],
  visualData: null,
  isLoading: false,
  error: null,

  initGame: async (world, player, runtimeId) => {
    set({ isLoading: true, error: null });
    try {
      const state = await gameApi.initGame(world, player, runtimeId);
      set({ 
        isStarted: true, 
        currentTurn: state.turn, 
        location: state.location,
        time: state.time,
        lastText: state.text || "Welcome to the game.",
        suggestions: state.suggestions || [],
        isLoading: false 
      });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  sendAction: async (action) => {
    set({ isLoading: true, error: null });
    try {
      const res = await gameApi.sendAction(action);
      if (res.success) {
        set((state) => ({
          lastText: res.text,
          npcReactions: res.npc_reactions,
          suggestions: res.suggestions,
          visualData: res.visual_data || null,  // 存储视觉数据
          // Optimistically update turn
          currentTurn: state.currentTurn + 1,
          isLoading: false
        }));
        // Background refresh state
        const state = await gameApi.getState();
        set({ location: state.location, time: state.time });
      } else {
        set({ error: res.error || "Action failed", isLoading: false });
      }
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  }
}));
