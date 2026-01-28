import { AnimatePresence, motion } from 'framer-motion';
import { X, Clock, ScrollText } from 'lucide-react';
import { HistoryEntry } from '../services/api';

interface Props {
  open: boolean;
  onClose: () => void;
  entries: HistoryEntry[];
  loading?: boolean;
}

const roleStyles: Record<string, { pill: string; accent: string }> = {
  player: {
    pill: 'bg-emerald-500/15 text-emerald-200 border-emerald-500/40',
    accent: 'border-emerald-500/60'
  },
  npc: {
    pill: 'bg-amber-500/15 text-amber-200 border-amber-500/40',
    accent: 'border-amber-500/60'
  },
  narrator: {
    pill: 'bg-sky-500/15 text-sky-200 border-sky-500/40',
    accent: 'border-sky-500/60'
  },
  system: {
    pill: 'bg-slate-500/15 text-slate-200 border-slate-500/40',
    accent: 'border-slate-500/60'
  }
};

const groupByTurn = (entries: HistoryEntry[]) => {
  const map = new Map<number, HistoryEntry[]>();
  entries.forEach((entry) => {
    const list = map.get(entry.turn) || [];
    list.push(entry);
    map.set(entry.turn, list);
  });
  return Array.from(map.entries())
    .map(([turn, items]) => ({ turn, items: items.sort((a, b) => a.seq - b.seq) }))
    .sort((a, b) => a.turn - b.turn);
};

export const HistoryDrawer = ({ open, onClose, entries, loading }: Props) => {
  const groups = groupByTurn(entries);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex justify-end"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.aside
            initial={{ x: 420, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 420, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 240, damping: 30 }}
            className="relative h-full w-full max-w-[420px] bg-gradient-to-br from-slate-950 via-slate-950/95 to-slate-900 border-l border-white/10 shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-5 border-b border-white/10">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/15 border border-sky-500/40">
                  <ScrollText className="text-sky-200" size={18} />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-white">History</h2>
                  <p className="text-xs text-slate-400">Conversation timeline</p>
                </div>
              </div>
              <button
                className="p-2 rounded-lg hover:bg-white/10 text-slate-300"
                onClick={onClose}
              >
                <X size={18} />
              </button>
            </div>

            <div className="px-6 py-4 h-[calc(100%-88px)] overflow-y-auto">
              {loading && (
                <div className="text-sm text-slate-400">Loading history...</div>
              )}

              {!loading && groups.length === 0 && (
                <div className="text-sm text-slate-500">No history yet.</div>
              )}

              <div className="space-y-6">
                {groups.map((group) => (
                  <div key={group.turn} className="space-y-3">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-slate-500">
                      <span className="h-px flex-1 bg-white/5" />
                      <span>Turn {group.turn}</span>
                      <span className="h-px flex-1 bg-white/5" />
                    </div>
                    <div className="space-y-3">
                      {group.items.map((entry) => {
                        const style = roleStyles[entry.role] || roleStyles.system;
                        return (
                          <div key={entry.id} className={`border-l-2 pl-4 ${style.accent}`}>
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`text-[11px] px-2 py-0.5 rounded-full border ${style.pill}`}
                              >
                                {entry.speaker_name}
                              </span>
                              <span className="flex items-center gap-1 text-[11px] text-slate-500">
                                <Clock size={12} />
                                {new Date(entry.timestamp).toLocaleTimeString()}
                              </span>
                            </div>
                            <div className="text-sm text-slate-200 leading-relaxed font-story">
                              {entry.content}
                            </div>
                            {entry.action && entry.action !== entry.content && (
                              <div className="text-xs text-slate-400 mt-1">{entry.action}</div>
                            )}
                            {entry.emotion && (
                              <div className="text-xs text-slate-500 mt-1">Emotion: {entry.emotion}</div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.aside>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
