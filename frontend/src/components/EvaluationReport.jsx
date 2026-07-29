import React, { useState, useEffect } from 'react';
import {
  Award,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Printer,
  Search,
  TrendingUp,
  MessageSquare,
  User,
  ChevronDown,
  ChevronUp,
  Quote,
  Loader2,
  RefreshCw,
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

/* ── Helpers ────────────────────────────────────────────────────────────── */

const pct = (v) => (v != null ? Math.round(v * 100) : null);

const METRIC_CONFIG = [
  { key: 'confidence_level', label: 'Confidence Level', color: 'accent' },
  { key: 'communication_clarity', label: 'Communication Clarity', color: 'purple' },
  { key: 'response_structure', label: 'Response Structure', color: 'emerald' },
  { key: 'candidate_engagement', label: 'Engagement', color: 'amber' },
];

const REC_MAP = {
  STRONG_HIRE: {
    cls: 'bg-emerald-muted text-emerald',
    label: 'Strong Hire',
    Icon: CheckCircle2,
  },
  HIRE: {
    cls: 'bg-emerald-muted text-emerald',
    label: 'Hire',
    Icon: CheckCircle2,
  },
  HOLD: {
    cls: 'bg-amber-muted text-amber',
    label: 'Hold / Re-vet',
    Icon: AlertTriangle,
  },
  REJECT: {
    cls: 'bg-rose-muted text-rose',
    label: 'Reject',
    Icon: XCircle,
  },
};

function getRecBadge(raw) {
  const key = (raw || 'HIRE').toUpperCase().replace(/\s+/g, '_');
  return (
    REC_MAP[key] || {
      cls: 'bg-accent-muted text-accent',
      label: raw || 'Hire',
      Icon: Award,
    }
  );
}

/* ── Component ──────────────────────────────────────────────────────────── */

export default function EvaluationReport({ interviewId, initialData = null }) {
  const [evaluation, setEvaluation] = useState(initialData);
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedTurn, setExpandedTurn] = useState(null);

  /* ── Data fetching & polling ─────────────────────────────────────────── */
  useEffect(() => {
    let isMounted = true;
    let pollCount = 0;
    const MAX_POLLS = 15; // up to ~75 seconds of polling
    let pollTimer = null;
    let fetchTimer = null;

    async function fetchEvaluation() {
      if (!interviewId) return;
      setError('');
      try {
        const queryParam = searchQuery ? `?q=${encodeURIComponent(searchQuery)}` : '';
        const res = await fetch(`${API_BASE}/api/interviews/${interviewId}/evaluation${queryParam}`, {
          headers: {
            'Content-Type': 'application/json',
            'X-User-Role': 'hr',
          },
        });
        if (res.status === 404) {
          // Evaluation not ready yet — poll again
          pollCount++;
          if (pollCount < MAX_POLLS) {
            pollTimer = setTimeout(fetchEvaluation, 5000);
          } else {
            if (isMounted) {
              setError('Evaluation report is taking longer than expected. Please refresh the page.');
              setLoading(false);
            }
          }
          return;
        }
        if (!res.ok) {
          throw new Error(`Failed to fetch evaluation: ${res.statusText}`);
        }
        const data = await res.json();
        if (isMounted) {
          setEvaluation(data);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || 'Error loading candidate evaluation report');
          setLoading(false);
        }
      }
    }

    if (initialData && !searchQuery) {
      setEvaluation(initialData);
      setLoading(false);
    } else {
      if (!evaluation) setLoading(true);
      fetchTimer = setTimeout(() => {
        fetchEvaluation();
      }, searchQuery ? 300 : 0);
    }

    return () => {
      isMounted = false;
      if (pollTimer) clearTimeout(pollTimer);
      if (fetchTimer) clearTimeout(fetchTimer);
    };
  }, [interviewId, initialData, searchQuery]);

  /* ── Handlers ────────────────────────────────────────────────────────── */
  const handlePrint = () => window.print();

  /* ── Loading state ───────────────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="card card-body flex flex-col items-center justify-center gap-4 py-16 text-center">
        <Loader2 size={32} className="text-accent animate-spin" />
        <div>
          <h4 className="text-base font-semibold text-[var(--color-text-primary)]">
            Generating Evaluation Report
          </h4>
          <p className="text-sm text-[var(--color-text-secondary)] mt-1">
            Analyzing transcript, behavioral metrics &amp; competency scores…
          </p>
        </div>
      </div>
    );
  }

  /* ── Error state ─────────────────────────────────────────────────────── */
  if (error) {
    return (
      <div className="card card-body flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-rose-muted flex items-center justify-center">
            <AlertTriangle size={18} className="text-rose" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">
              Evaluation Error
            </h4>
            <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">{error}</p>
          </div>
        </div>
        <button onClick={() => window.location.reload()} className="btn btn-secondary btn-sm">
          <RefreshCw size={14} />
          Retry
        </button>
      </div>
    );
  }

  /* ── Derived data ────────────────────────────────────────────────────── */
  const rec = evaluation?.final_recommendation || {};
  const metrics = evaluation?.behavioral_metrics || {};
  const competencies = evaluation?.detailed_competencies || [];
  const turns = evaluation?.full_transcript_evaluations || [];
  const candidateId = evaluation?.candidate_id || 'Candidate';
  const overallFit =
    evaluation?.scorecard?.overall_fit != null
      ? Math.round(evaluation.scorecard.overall_fit * 100)
      : Math.round(rec.overall_suitability_score || 85);

  const badge = getRecBadge(rec.hiring_recommendation);
  const filteredTurns = turns;

  /* ── Render ──────────────────────────────────────────────────────────── */
  return (
    <div className="space-y-6 print:text-black print:bg-white">
      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="card">
        <div className="card-header flex-wrap">
          {/* Left: candidate info */}
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-accent-muted flex items-center justify-center shrink-0">
              <User size={20} className="text-accent" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-[var(--color-text-primary)] leading-tight">
                {candidateId}
              </h2>
              <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                Evaluated {rec.evaluated_at ? new Date(rec.evaluated_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : 'just now'}
                <span className="mx-1.5 opacity-40">·</span>
                Interview {interviewId}
              </p>
            </div>
          </div>

          {/* Right: score, badge, print */}
          <div className="flex items-center gap-3 no-print">
            {/* Score */}
            <div className="text-right mr-1">
              <span className="block text-[10px] uppercase tracking-widest text-[var(--color-text-muted)] font-semibold">
                Score
              </span>
              <span className="text-3xl font-extrabold font-mono text-accent leading-none">
                {overallFit}
              </span>
            </div>

            {/* Recommendation badge */}
            <span className={`badge text-xs px-3 py-1.5 ${badge.cls}`}>
              <badge.Icon size={14} />
              {badge.label}
            </span>

            {/* Print / Export */}
            <button onClick={handlePrint} className="btn btn-secondary btn-sm" title="Print or export PDF">
              <Printer size={14} />
              Export
            </button>
          </div>
        </div>

        {/* Executive summary */}
        <div className="card-body">
          <div className="border-l-2 border-[var(--color-accent)] pl-4 py-1">
            <p className="text-sm text-[var(--color-text-primary)] leading-relaxed">
              {rec.executive_summary || 'No summary generated yet.'}
            </p>
          </div>
        </div>
      </div>

      {/* ── Behavioral Metrics ───────────────────────────────────────────── */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
            <TrendingUp size={16} className="text-accent" />
            Behavioral Metrics
          </h3>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {METRIC_CONFIG.map(({ key, label, color }) => {
              const raw = metrics[key];
              const value = pct(raw);
              return (
                <div
                  key={key}
                  className="rounded-xl border border-[var(--color-glass-border)] bg-[var(--color-glass-base)] p-4 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-[var(--color-text-secondary)]">{label}</span>
                    <span className={`text-sm font-bold font-mono text-${color}`}>
                      {value != null ? `${value}%` : '—'}
                    </span>
                  </div>
                  <div className="progress-track">
                    <div
                      className={`progress-fill bg-${color === 'accent' ? '[var(--color-accent)]' : color === 'purple' ? '[var(--color-purple)]' : color === 'emerald' ? '[var(--color-emerald)]' : '[var(--color-amber)]'}`}
                      style={{ width: value != null ? `${value}%` : '0%' }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Competencies Matrix ──────────────────────────────────────────── */}
      {competencies.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
              <Award size={16} className="text-accent" />
              Competencies
            </h3>
          </div>
          <div className="card-body">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {competencies.map((comp, idx) => (
                <div
                  key={idx}
                  className="rounded-xl border border-[var(--color-glass-border)] bg-[var(--color-glass-base)] p-5 space-y-4"
                >
                  {/* Name + accuracy */}
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-semibold text-[var(--color-text-primary)] capitalize">
                      {comp.competency_id?.replace(/_/g, ' ')}
                    </span>
                    <span className="badge bg-accent-muted text-accent">
                      {comp.technical_accuracy}%
                    </span>
                  </div>

                  {/* Accuracy bar */}
                  <div className="progress-track">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${comp.technical_accuracy}%`,
                        background: 'linear-gradient(90deg, var(--color-accent), var(--color-purple))',
                      }}
                    />
                  </div>

                  {/* Strengths */}
                  {comp.strengths?.length > 0 && (
                    <div>
                      <h4 className="text-[11px] font-semibold uppercase tracking-wider text-emerald mb-1.5">
                        Strengths
                      </h4>
                      <ul className="space-y-1">
                        {comp.strengths.map((s, i) => (
                          <li key={i} className="text-xs text-[var(--color-text-secondary)] flex items-start gap-2">
                            <CheckCircle2 size={12} className="text-emerald shrink-0 mt-0.5" />
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Improvement areas */}
                  {comp.areas_for_improvement?.length > 0 && (
                    <div>
                      <h4 className="text-[11px] font-semibold uppercase tracking-wider text-amber mb-1.5">
                        Areas for Improvement
                      </h4>
                      <ul className="space-y-1">
                        {comp.areas_for_improvement.map((imp, i) => (
                          <li key={i} className="text-xs text-[var(--color-text-secondary)] flex items-start gap-2">
                            <AlertTriangle size={12} className="text-amber shrink-0 mt-0.5" />
                            {imp}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Verbatim quotes */}
                  {comp.quotes?.length > 0 && (
                    <div className="pt-3 border-t border-[var(--color-glass-border)] space-y-2">
                      <h4 className="text-[11px] font-semibold uppercase tracking-wider text-purple flex items-center gap-1">
                        <Quote size={11} /> Verbatim
                      </h4>
                      {comp.quotes.map((q, i) => (
                        <p
                          key={i}
                          className="text-xs italic text-[var(--color-text-secondary)] bg-purple-muted rounded-lg px-3 py-2 leading-relaxed"
                        >
                          "{q}"
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Q&A Transcript ───────────────────────────────────────────────── */}
      <div className="card">
        <div className="card-header flex-wrap">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
            <MessageSquare size={16} className="text-accent" />
            Q&amp;A Transcript
          </h3>
          <div className="relative w-full sm:w-64 no-print">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
            <input
              type="text"
              placeholder="Search transcript…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-9 !text-sm"
            />
          </div>
        </div>

        <div className="card-body space-y-2">
          {filteredTurns.length === 0 ? (
            <p className="py-10 text-center text-sm text-[var(--color-text-muted)]">
              No matching transcript turns found.
            </p>
          ) : (
            filteredTurns.map((turn, idx) => {
              const isExpanded = expandedTurn === idx;
              return (
                <div
                  key={idx}
                  className="rounded-xl border border-[var(--color-glass-border)] bg-[var(--color-glass-base)] transition-colors hover:border-[var(--color-glass-border-strong)]"
                >
                  {/* Accordion header */}
                  <button
                    onClick={() => setExpandedTurn(isExpanded ? null : idx)}
                    className="w-full flex items-center justify-between gap-3 px-4 py-3 text-left cursor-pointer"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="badge bg-purple-muted text-purple shrink-0">
                        #{turn.question_number || idx + 1}
                      </span>
                      <span className="text-sm text-[var(--color-text-primary)] truncate">
                        {turn.question}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="badge bg-accent-muted text-accent">
                        {Math.round((turn.confidence_score || 0.85) * 100)}%
                      </span>
                      <span className="badge bg-emerald-muted text-emerald">
                        {turn.technical_accuracy || 85}%
                      </span>
                      {isExpanded ? (
                        <ChevronUp size={16} className="text-[var(--color-text-muted)]" />
                      ) : (
                        <ChevronDown size={16} className="text-[var(--color-text-muted)]" />
                      )}
                    </div>
                  </button>

                  {/* Expanded content */}
                  {isExpanded && (
                    <div className="px-4 pb-4 space-y-3 animate-fade-in">
                      {/* Question */}
                      <div>
                        <span className="text-[11px] uppercase tracking-wider font-semibold text-[var(--color-text-muted)]">
                          Question
                        </span>
                        <p className="text-sm text-[var(--color-text-primary)] mt-1 leading-relaxed">
                          {turn.question}
                        </p>
                      </div>

                      {/* Answer */}
                      <div className="border-l-2 border-[var(--color-purple)] pl-3">
                        <span className="text-[11px] uppercase tracking-wider font-semibold text-[var(--color-text-muted)]">
                          Answer
                        </span>
                        <p className="text-sm text-[var(--color-text-secondary)] mt-1 leading-relaxed">
                          {turn.candidate_answer}
                        </p>
                      </div>

                      {/* Evaluator notes */}
                      {turn.evaluator_notes && (
                        <div className="rounded-lg bg-accent-muted px-3 py-2.5 flex items-start gap-2">
                          <MessageSquare size={13} className="text-accent shrink-0 mt-0.5" />
                          <p className="text-xs text-accent leading-relaxed">
                            {turn.evaluator_notes}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
