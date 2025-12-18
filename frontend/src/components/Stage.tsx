import { useState, useEffect } from 'react';
import { useGameStore } from '../store/gameStore';
import { DialogueBox } from './DialogueBox';
import { ArrowRight, Loader2, Mic, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { parseBackendText } from '../utils/textParser';

export const Stage = () => {
  const { 
    location, 
    time, 
    lastText, 
    npcReactions, 
    suggestions,
    sendAction,
    isLoading 
  } = useGameStore();

  const [textQueue, setTextQueue] = useState<string[]>([]);
  const [currentLineIndex, setCurrentLineIndex] = useState(0);

  // Parse text when lastText changes
  useEffect(() => {
    const queue = parseBackendText(lastText);
    setTextQueue(queue);
    setCurrentLineIndex(0);
  }, [lastText]);

  const [input, setInput] = useState('');

  const handleAdvance = () => {
    if (currentLineIndex < textQueue.length - 1) {
      setCurrentLineIndex(prev => prev + 1);
    }
  };

  const isDialogueFinished = currentLineIndex >= textQueue.length - 1;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      sendAction(input);
      setInput('');
    }
  };

  const activeSpeaker = npcReactions.length > 0 ? npcReactions[0].character_name : undefined;
  
  // Display text is the current line in the queue
  const displayText = textQueue.length > 0 ? textQueue[currentLineIndex] : "...";

  return (
    <div 
      className="relative w-full h-screen bg-slate-950 overflow-hidden font-sans select-none cursor-pointer"
      onClick={handleAdvance} // Click anywhere to advance
    >
      
      {/* Background Layer */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-indigo-900/40 via-slate-900 to-black z-0 pointer-events-none">
        <div className="absolute inset-0 flex items-center justify-center opacity-10">
           {/* Abstract Background Grid */}
           <div className="w-[200%] h-[200%] bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:40px_40px] transform rotate-12" />
        </div>
        <div className="absolute inset-0 flex items-center justify-center">
          <h1 className="text-9xl font-black text-white/5 uppercase tracking-[0.2em] blur-sm scale-150">
            {location}
          </h1>
        </div>
      </div>

      {/* Characters Layer */}
      <div className="absolute inset-0 pointer-events-none flex items-end justify-center pb-32 gap-12 z-10 perspective-1000">
        <AnimatePresence mode='popLayout'>
        {npcReactions.map((reaction, idx) => (
           <motion.div 
             key={idx + reaction.character_name}
             initial={{ opacity: 0, scale: 0.9, y: 20 }}
             animate={{ opacity: 1, scale: 1, y: 0 }}
             exit={{ opacity: 0, scale: 0.95 }}
             transition={{ duration: 0.4 }}
             className="flex flex-col items-center group"
           >
              <div className="w-80 h-[500px] bg-gradient-to-b from-indigo-500/10 to-slate-900/50 rounded-2xl border border-indigo-500/20 backdrop-blur-sm flex items-center justify-center relative shadow-[0_0_30px_rgba(79,70,229,0.1)] group-hover:shadow-[0_0_50px_rgba(79,70,229,0.2)] transition-shadow duration-500">
                 {/* Placeholder Avatar */}
                 <span className="text-8xl filter drop-shadow-[0_0_10px_rgba(255,255,255,0.5)]">👤</span>
                 
                 {reaction.emotion && (
                    <div className="absolute -top-4 -right-4 bg-white text-slate-900 p-2 rounded-full shadow-lg text-2xl animate-bounce">
                       {reaction.emotion === '开心' ? '😄' : 
                        reaction.emotion === '生气' ? '😠' : 
                        reaction.emotion === '悲伤' ? '😢' : '😐'}
                    </div>
                 )}
              </div>
           </motion.div>
        ))}
        </AnimatePresence>
      </div>

      {/* HUD Info */}
      <div className="absolute top-6 left-6 flex flex-col gap-2 z-30 pointer-events-none">
        <div className="flex items-center gap-3 bg-black/40 backdrop-blur-md px-4 py-2 rounded-full border border-white/5 shadow-xl">
           <span className="text-blue-400"><Sparkles size={16} /></span>
           <span className="text-slate-200 text-sm font-medium tracking-wide">📍 {location}</span>
           <span className="w-px h-4 bg-white/10" />
           <span className="text-slate-300 text-sm">🕒 {time}</span>
        </div>
      </div>

      {/* Main Interaction Layer */}
      <div className="absolute inset-0 flex flex-col justify-end z-20 pointer-events-none">
        
        {/* Dialogue Box */}
        <div className="relative z-30 pointer-events-auto">
             <DialogueBox 
                text={displayText} 
                npcName={activeSpeaker} 
                hasNext={!isDialogueFinished} // Pass hasNext prop
             />
        </div>

        {/* Input Area - Only show when dialogue is finished */}
        <AnimatePresence>
        {isDialogueFinished && (
            <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                className="w-full bg-gradient-to-t from-black via-black/80 to-transparent pb-6 pt-12 px-4 pointer-events-auto"
                onClick={(e) => e.stopPropagation()} // Prevent click through to advance
            >
                <div className="max-w-4xl mx-auto flex flex-col gap-4">
                    
                    {/* Suggestions */}
                    {suggestions && suggestions.length > 0 && (
                    <div 
                        className="flex flex-wrap justify-center gap-3"
                    >
                        {suggestions.map((s, idx) => (
                        <button
                            key={idx}
                            onClick={() => sendAction(s)}
                            disabled={isLoading}
                            className="bg-indigo-600/20 hover:bg-indigo-500/30 backdrop-blur-md border border-indigo-500/30 text-indigo-100 px-5 py-2 rounded-full transition-all text-sm font-medium shadow-lg hover:scale-105 hover:shadow-indigo-500/20 ring-1 ring-inset ring-indigo-500/20"
                        >
                            {s}
                        </button>
                        ))}
                    </div>
                    )}

                    {/* Input Bar */}
                    <form onSubmit={handleSubmit} className="relative flex items-center gap-3">
                        <button 
                        type="button"
                        className="p-3.5 rounded-xl bg-slate-800/80 text-slate-400 hover:bg-slate-700/80 hover:text-white transition-all border border-slate-700/50 backdrop-blur"
                        >
                        <Mic size={20} />
                        </button>
                        
                        <div className="flex-1 relative group">
                            <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-xl opacity-30 group-hover:opacity-60 transition duration-500 blur"></div>
                            <input 
                            type="text" 
                            className="relative w-full bg-slate-900/90 backdrop-blur-xl rounded-xl border border-white/10 px-5 py-3.5 text-white focus:outline-none placeholder-slate-500 shadow-inner"
                            placeholder="What will you do?..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            disabled={isLoading}
                            />
                        </div>

                        <button 
                        type="submit" 
                        className="bg-gradient-to-br from-blue-600 to-indigo-700 hover:from-blue-500 hover:to-indigo-600 text-white px-6 py-3.5 rounded-xl font-bold transition-all shadow-lg shadow-blue-900/20 disabled:opacity-50 disabled:grayscale flex items-center justify-center min-w-[60px]"
                        disabled={!input.trim() || isLoading}
                        >
                        {isLoading ? <Loader2 className="animate-spin" /> : <ArrowRight />}
                        </button>
                    </form>
                </div>
            </motion.div>
        )}
        </AnimatePresence>
      </div>

    </div>
  );
};
