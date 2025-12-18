import { useState, useEffect } from 'react';
import { useGameStore } from './store/gameStore';
import { gameApi } from './services/api';
import { Loader2, Play, Plus } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Stage } from './components/Stage';
import { ErrorBoundary } from './components/ErrorBoundary';

function App() {
  const { isStarted, initGame, isLoading, error } = useGameStore();
  const [worlds, setWorlds] = useState<string[]>([]);
  const [selectedWorld, setSelectedWorld] = useState('');
  const [runtimes, setRuntimes] = useState<{id: string, name: string, initialized_at: string, turn: number}[]>([]);
  const [view, setView] = useState<'world_select' | 'save_select'>('world_select');
  const [playerName, setPlayerName] = useState('Traveler');

  useEffect(() => {
    gameApi.getWorlds().then(setWorlds).catch(console.error);
  }, []);

  const handleWorldSelect = async (world: string) => {
    setSelectedWorld(world);
    try {
      const saves = await gameApi.getRuntimes(world);
      setRuntimes(saves);
      setView('save_select');
    } catch (e) {
      console.error(e);
    }
  };

  const handleStartNew = () => {
    if (selectedWorld && playerName) {
      initGame(selectedWorld, playerName);
    }
  };

  const handleLoadSave = (runtimeId: string) => {
    if (selectedWorld) {
      initGame(selectedWorld, playerName, runtimeId); // Player name might be ignored by backend for load
    }
  };

// ... (imports)

  if (isStarted) {
    return (
      <ErrorBoundary>
        <Stage />
      </ErrorBoundary>
    );
  }

  return (
    <div className="w-full h-screen bg-slate-950 text-white flex flex-col items-center justify-center p-8 relative overflow-hidden font-sans">
      
      {/* Background Decor */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-indigo-900/20 via-slate-950 to-black pointer-events-none" />
      <div className="absolute top-0 w-full h-px bg-gradient-to-r from-transparent via-blue-500 to-transparent opacity-20" />
      <div className="absolute bottom-0 w-full h-px bg-gradient-to-r from-transparent via-purple-500 to-transparent opacity-20" />

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-2xl w-full relative z-10"
      >
        <div className="text-center mb-12">
          <h1 className="text-6xl font-black tracking-tight mb-2 bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent filter drop-shadow-[0_0_15px_rgba(59,130,246,0.5)]">
            AAA StoryMaker
          </h1>
          <p className="text-slate-400 text-lg font-light tracking-widest uppercase">Interactive GalGame Engine</p>
        </div>

        <div className="bg-slate-900/50 backdrop-blur-xl border border-white/10 rounded-3xl p-8 shadow-2xl">
          <AnimatePresence mode="wait">
            
            {/* View 1: World Selection */}
            {view === 'world_select' && (
              <motion.div
                key="world-select"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="space-y-6"
              >
                <h2 className="text-xl font-medium text-slate-300 mb-4 border-b border-white/5 pb-2">Select World</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {worlds.map(world => (
                    <button
                      key={world}
                      onClick={() => handleWorldSelect(world)}
                      className="group relative overflow-hidden bg-white/5 hover:bg-white/10 border border-white/10 hover:border-blue-500/50 rounded-xl p-6 text-left transition-all duration-300"
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/0 via-blue-500/0 to-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity" />
                      <span className="text-2xl font-bold text-white group-hover:text-blue-200 transition-colors">{world}</span>
                    </button>
                  ))}
                </div>
                {worlds.length === 0 && (
                   <div className="text-center text-slate-500 py-8">No worlds found. Please run creator tool first.</div>
                )}
              </motion.div>
            )}

            {/* View 2: Save Selection */}
            {view === 'save_select' && (
              <motion.div
                key="save-select"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-4">
                  <button 
                    onClick={() => setView('world_select')}
                    className="text-sm text-slate-500 hover:text-white transition-colors"
                  >
                    ← Back
                  </button>
                  <h2 className="text-xl font-medium text-slate-300">
                    Entering <span className="text-blue-400 font-bold">{selectedWorld}</span>
                  </h2>
                </div>

                {/* New Game Section */}
                <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-6">
                  <h3 className="text-blue-300 font-bold mb-4 flex items-center gap-2">
                    <Plus size={18} /> New Game
                  </h3>
                  <div className="flex gap-2">
                    <input 
                      type="text" 
                      className="flex-1 bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
                      placeholder="Enter Player Name"
                      value={playerName}
                      onChange={(e) => setPlayerName(e.target.value)}
                    />
                    <button
                      onClick={handleStartNew}
                      disabled={isLoading || !playerName}
                      className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-lg font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      {isLoading ? <Loader2 className="animate-spin" size={18}/> : <Play size={18} />} Start
                    </button>
                  </div>
                </div>

                {/* Save List */}
                <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                  <h3 className="text-slate-400 text-sm font-bold uppercase tracking-wider mb-2">Load Save</h3>
                  {runtimes.length === 0 && (
                    <div className="text-slate-600 italic text-center py-4">No saves found. Start a new game!</div>
                  )}
                  {runtimes.map(rt => (
                    <button
                      key={rt.id}
                      onClick={() => handleLoadSave(rt.id)}
                      disabled={isLoading}
                      className="w-full flex items-center justify-between bg-white/5 hover:bg-white/10 border border-white/5 hover:border-white/20 rounded-lg p-4 group transition-all"
                    >
                      <div className="flex flex-col items-start">
                        <span className="font-bold text-slate-200 group-hover:text-white transition-colors">
                          {rt.name}
                        </span>
                        <span className="text-xs text-slate-500">
                          {new Date(rt.initialized_at).toLocaleString()}
                        </span>
                      </div>
                      <span className="bg-white/5 p-2 rounded-full opacity-0 group-hover:opacity-100 transition-opacity text-blue-400">
                         {isLoading ? <Loader2 className="animate-spin" size={16}/> : <Play size={16} fill="currentColor" />}
                      </span>
                    </button>
                  ))}
                </div>

              </motion.div>
            )}

            {error && (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-6 p-4 bg-red-500/20 border border-red-500/50 rounded-xl text-red-200 text-sm"
              >
                Error: {error}
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}
export default App;
