import React, { useEffect, useState, useRef } from 'react';
import { MessageCircle, Loader2 } from 'lucide-react';

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
    <div className="card h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-white/[0.06]">
        <div className="w-9 h-9 rounded-lg bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-cyan-400">
          <MessageCircle size={18} />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white/90">Interview Transcript</h3>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
            </span>
            <span className="text-[11px] text-emerald-400 font-medium">Live</span>
          </div>
        </div>
      </div>

      {/* Transcript body */}
      <div
        className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-3"
        ref={scrollRef}
      >
        {loading ? (
          <div className="h-full flex flex-col items-center justify-center gap-3 text-white/40">
            <Loader2 size={24} className="animate-spin" />
            <span className="text-sm">Connecting...</span>
          </div>
        ) : transcript.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center gap-3 text-white/30 text-center px-6">
            <MessageCircle size={32} strokeWidth={1.5} />
            <p className="text-sm leading-relaxed max-w-[280px]">
              No transcript yet. Start an interview to see the conversation here.
            </p>
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
                className={`flex flex-col max-w-[80%] transition-opacity duration-300 ${
                  isCandidate ? 'self-start items-start' : 'self-end items-end'
                }`}
              >
                <span
                  className={`text-[11px] font-medium mb-1 ${
                    isCandidate ? 'text-purple-400/80' : 'text-cyan-400/80'
                  }`}
                >
                  {isCandidate ? 'Candidate' : 'Interviewer'}
                </span>
                <div
                  className={`px-4 py-2.5 rounded-2xl text-[13.5px] leading-relaxed border ${
                    isCandidate
                      ? 'bg-purple-500/[0.08] border-purple-500/[0.12] text-white/85 rounded-tl-md'
                      : 'bg-cyan-500/[0.08] border-cyan-500/[0.12] text-white/85 rounded-tr-md'
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
