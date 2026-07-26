import React, { useEffect, useState, useRef } from 'react';
import { Activity } from 'lucide-react';

export default function TranscriptStream({ supabase, interviewId }) {
  const [transcript, setTranscript] = useState([]);
  const [loading, setLoading] = useState(true);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (!supabase || !interviewId) return;

    setLoading(true);
    setTranscript([]);

    const fetchTranscript = async () => {
      const { data, error } = await supabase
        .from('interviews')
        .select('transcript')
        .eq('id', interviewId)
        .single();
      
      if (!error && data && data.transcript) {
        setTranscript(data.transcript);
      }
      setLoading(false);
    };

    fetchTranscript();

    const channel = supabase
      .channel(`transcript:${interviewId}`)
      .on('postgres_changes', 
        { event: 'UPDATE', schema: 'public', table: 'interviews', filter: `id=eq.${interviewId}` },
        (payload) => {
          if (payload.new.transcript) {
            setTranscript(payload.new.transcript);
          }
        }
      )
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, [supabase, interviewId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcript]);

  return (
    <div className="glass-panel glass-panel-cyan flex flex-col h-full overflow-hidden relative">
      <div className="flex items-center gap-3 p-4 border-b border-[var(--color-glass-border)] bg-[rgba(255,255,255,0.02)]">
        <div className="w-10 h-10 rounded-xl bg-[var(--color-glass-hover)] border border-[var(--color-glass-border-strong)] flex items-center justify-center text-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.2)]">
          <Activity size={20} className="animate-pulse-neon" />
        </div>
        <div>
          <h3 className="text-base font-medium">Mission Control Stream</h3>
          <span className="text-[11px] font-mono text-cyan-400 tracking-wider">LIVE DUAL-CHANNEL</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-4" ref={scrollRef}>
        {loading ? (
          <div className="h-full flex items-center justify-center text-[var(--color-text-muted)] gap-3 font-mono text-sm">
            <div className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse"></div>
            Connecting to secure channel...
          </div>
        ) : transcript.length === 0 ? (
          <div className="h-full flex items-center justify-center text-[var(--color-text-muted)] italic text-sm">
            Waiting for audio transmission...
          </div>
        ) : (
          transcript.map((item, idx) => {
            let isCandidate = false;
            let cleanLine = '';
            
            if (typeof item === 'string') {
              isCandidate = item.toLowerCase().startsWith('candidate:');
              cleanLine = item.replace(/^(candidate:|interviewer:)\s*/i, '');
            } else if (item && typeof item === 'object') {
              isCandidate = item.speaker?.toLowerCase() === 'candidate';
              cleanLine = item.text || '';
            }
            
            return (
              <div 
                key={idx} 
                className={`animate-slide-in-3d flex flex-col max-w-[80%] ${isCandidate ? 'self-start' : 'self-end'}`}
              >
                <span className={`text-[10px] font-mono mb-1 tracking-wider ${isCandidate ? 'text-purple-400' : 'text-cyan-400'}`}>
                  {isCandidate ? 'CANDIDATE' : 'SYSTEM'}
                </span>
                <div 
                  className={`px-4 py-3 rounded-2xl text-[14px] leading-relaxed shadow-lg backdrop-blur-md border ${
                    isCandidate 
                      ? 'bg-[rgba(168,85,247,0.1)] border-[rgba(168,85,247,0.2)] text-[var(--color-text-primary)] rounded-tl-sm' 
                      : 'bg-[rgba(6,182,212,0.1)] border-[rgba(6,182,212,0.2)] text-[var(--color-text-primary)] rounded-tr-sm'
                  }`}
                >
                  {cleanLine}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
