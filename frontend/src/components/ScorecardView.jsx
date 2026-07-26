import React, { useEffect, useState } from 'react';
import { ClipboardCheck } from 'lucide-react';

export default function ScorecardView({ supabase, interviewId }) {
  const [scorecard, setScorecard] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!supabase || !interviewId) return;

    setLoading(true);
    setScorecard(null);

    const fetchScorecard = async () => {
      const { data, error } = await supabase
        .from('scorecards')
        .select('*')
        .eq('interview_id', interviewId)
        .order('created_at', { ascending: false })
        .limit(1)
        .single();
        
      if (!error && data) {
        setScorecard(data.scorecard);
      }
      setLoading(false);
    };

    fetchScorecard();

    const channel = supabase
      .channel(`scorecard:${interviewId}`)
      .on('postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'scorecards', filter: `interview_id=eq.${interviewId}` },
        (payload) => setScorecard(payload.new.scorecard)
      )
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, [supabase, interviewId]);

  return (
    <div className="glass-panel flex flex-col h-full overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-[var(--color-glass-border)] bg-[rgba(255,255,255,0.02)]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[var(--color-glass-hover)] border border-[var(--color-glass-border-strong)] flex items-center justify-center text-teal-400 shadow-[0_0_10px_rgba(45,212,191,0.2)]">
            <ClipboardCheck size={20} />
          </div>
          <div>
            <h3 className="text-base font-medium">Extractive Scorecard</h3>
            <span className="text-[11px] font-mono text-teal-400 tracking-wider">
              {scorecard ? `OVERALL FIT: ${(scorecard.overall_fit * 100).toFixed(0)}%` : 'PENDING EVALUATION'}
            </span>
          </div>
        </div>
        
        {scorecard?.needs_human_review && (
          <div className="px-3 py-1 bg-[rgba(245,158,11,0.1)] text-amber-500 border border-[rgba(245,158,11,0.3)] rounded text-xs font-medium">
            Needs Human Review
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
        {loading ? (
          <div className="h-full flex items-center justify-center text-[var(--color-text-muted)] gap-3 font-mono text-sm">
            <div className="w-2 h-2 rounded-full bg-teal-500 animate-pulse"></div>
            Awaiting scorecard synthesis...
          </div>
        ) : !scorecard ? (
          <div className="h-full flex items-center justify-center text-[var(--color-text-muted)] italic text-sm">
            Analytics agent will evaluate post-call.
          </div>
        ) : (
          scorecard.competencies.map((c, i) => (
            <div key={i} className="bg-[rgba(255,255,255,0.01)] border border-[var(--color-glass-border)] rounded-lg p-5">
              <div className="flex justify-between items-center mb-4">
                <strong className="text-white text-sm">{c.competency_id}</strong>
                <span className={`font-mono text-xs ${c.demonstrated_level === 'insufficient_evidence' ? 'text-rose-500' : 'text-teal-400 drop-shadow-[0_0_5px_rgba(45,212,191,0.5)]'}`}>
                  {c.demonstrated_level.toUpperCase()}
                </span>
              </div>

              {c.evidence_quotes.length === 0 ? (
                <div className="text-[var(--color-text-muted)] text-xs italic">
                  No verified quotes extracted.
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  {c.evidence_quotes.map((q, idx) => (
                    <div key={idx} className="border-l-2 border-teal-500 pl-4 py-2 bg-[rgba(45,212,191,0.05)] rounded-r-md text-sm text-[var(--color-text-secondary)] font-sans italic leading-relaxed">
                      "{q.quote}"
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
