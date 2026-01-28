import { motion } from 'framer-motion';
import { Typewriter } from './Typewriter';
import { ChevronDown } from 'lucide-react';

interface Props {
  text: string;
  npcName?: string;
  hasNext?: boolean;
}

export const DialogueBox = ({ text, npcName, hasNext }: Props) => {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="absolute bottom-6 w-full px-4 md:px-12 lg:px-24 z-20 pointer-events-none"
    >
      <div className="max-w-5xl mx-auto relative group pointer-events-auto">
        
        {/* Name Tag */}
        {npcName && (
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="absolute -top-5 left-4 md:left-8 z-30"
          >
            <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-1.5 rounded-t-lg rounded-br-lg shadow-[0_4px_20px_rgba(37,99,235,0.4)] backdrop-blur-md border border-white/10">
              <span className="font-bold tracking-wider text-lg text-shadow-sm">{npcName}</span>
            </div>
          </motion.div>
        )}

        {/* Main Box */}
        <div className="bg-slate-950/80 backdrop-blur-xl border border-white/10 rounded-2xl p-6 md:p-8 shadow-[0_8px_32px_rgba(0,0,0,0.5)] min-h-[180px] relative overflow-hidden">
          
          {/* Decorative Elements */}
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-blue-500/50 to-transparent opacity-50" />
          <div className="absolute -right-10 -bottom-10 w-40 h-40 bg-blue-500/10 blur-3xl rounded-full pointer-events-none" />

          {/* Text Content */}
          <div className="relative z-10 text-lg md:text-xl leading-relaxed text-slate-100 font-story tracking-wide min-h-[4rem] text-shadow-sm">
            <Typewriter text={text} speed={25} />
          </div>

          {/* Next Indicator */}
          {hasNext && (
            <div className="absolute bottom-4 right-6 animate-bounce text-blue-400 opacity-80">
              <ChevronDown size={28} />
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};
