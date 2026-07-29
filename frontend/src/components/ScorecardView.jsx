import React, { useEffect, useState } from 'react';
import { Award } from 'lucide-react';

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

  const fitPercent = scorecard ? Math.round(scorecard.overall_fit * 100) : 0;

  /* Map demonstrated_level to accent colours */
  const levelColor = (level) => {
    switch (level) {
      case 'strong':         return { text: 'text-emerald', bg: 'bg-emerald-muted' };
      case 'moderate':       return { text: 'text-accent',  bg: 'bg-accent-muted'  };
      case 'developing':     return { text: 'text-amber',   bg: 'bg-amber-muted'   };
      case 'insufficient_evidence':
      default:               return { text: 'text-rose',    bg: 'bg-rose-muted'    };
    }
  };

  return (
    <div className="card flex flex-col h-full overflow-hidden">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="card-header">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-[var(--color-accent-muted)] flex items-center justify-center text-accent">
            <Award size={18} />
          </div>
          <h3 className="text-sm font-semibold tracking-wide text-[var(--color-text-primary)]">
            Candidate Scorecard
          </h3>
        </div>

        {scorecard?.needs_human_review && (
          <span className="badge text-amber bg-amber-muted border border-[rgba(251,191,36,0.25)]">
            Needs Human Review
          </span>
        )}
      </div>

      {/* ── Body ────────────────────────────────────────────────── */}
      <div className="card-body flex-1 overflow-y-auto flex flex-col gap-5">
        {loading ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 py-16">
            <div className="w-2 h-2 rounded-full bg-[var(--color-accent)] animate-pulse-soft" />
            <span className="text-sm font-mono text-[var(--color-text-muted)]">
              Generating scorecard…
            </span>
          </div>
        ) : !scorecard ? (
          <div className="flex-1 flex items-center justify-center py-16">
            <p className="text-sm text-[var(--color-text-muted)] text-center max-w-[260px] leading-relaxed">
              Scorecard will appear after the interview evaluation completes.
            </p>
          </div>
        ) : (
          <>
            {/* ── Overall Fit ─────────────────────────────────── */}
            <div className="flex flex-col items-center gap-3 py-4">
              <span className="text-5xl font-bold tracking-tight text-[var(--color-text-primary)]">
                {fitPercent}
                <span className="text-2xl font-semibold text-[var(--color-text-secondary)]">%</span>
              </span>
              <span className="text-xs font-mono uppercase tracking-widest text-[var(--color-text-muted)]">
                Overall Fit
              </span>

              <div className="progress-track w-48 mt-1">
                <div
                  className="progress-fill"
                  style={{
                    width: `${fitPercent}%`,
                    background: `linear-gradient(90deg, var(--color-accent), var(--color-purple))`,
                  }}
                />
              </div>
            </div>

            {/* ── Competency Cards ────────────────────────────── */}
            <div className="flex flex-col gap-4">
              {scorecard.competencies.map((c, i) => {
                const color = levelColor(c.demonstrated_level);
                return (
                  <div
                    key={i}
                    className="card p-4 animate-fade-in"
                    style={{ animationDelay: `${i * 60}ms` }}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-medium text-[var(--color-text-primary)]">
                        {c.competency_id}
                      </span>
                      <span className={`badge ${color.text} ${color.bg}`}>
                        {c.demonstrated_level.replace(/_/g, ' ')}
                      </span>
                    </div>

                    {c.evidence_quotes.length === 0 ? (
                      <p className="text-xs text-[var(--color-text-muted)] italic">
                        No evidence quotes extracted.
                      </p>
                    ) : (
                      <div className="flex flex-col gap-2">
                        {c.evidence_quotes.map((q, idx) => (
                          <blockquote
                            key={idx}
                            className="border-l-2 border-[var(--color-accent)] pl-3 py-1.5 text-[13px] leading-relaxed text-[var(--color-text-secondary)] italic"
                          >
                            "{q.quote}"
                          </blockquote>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
