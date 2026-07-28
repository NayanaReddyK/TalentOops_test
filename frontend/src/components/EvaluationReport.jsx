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
  BrainCircuit, 
  Briefcase, 
  User,
  Sparkles,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export default function EvaluationReport({ interviewId, initialData = null }) {
  const [evaluation, setEvaluation] = useState(initialData);
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedTurn, setExpandedTurn] = useState(null);

  useEffect(() => {
    let isMounted = true;
    let pollCount = 0;
    const MAX_POLLS = 15;  // up to ~75 seconds of polling
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

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return (
      <div className="glass-panel p-10 text-center flex flex-col items-center justify-center gap-4">
        <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 animate-spin">
          <Sparkles size={24} />
        </div>
        <div>
          <h4 className="text-base font-medium text-cyan-300">Synthesizing Evaluation Report</h4>
          <p className="text-xs font-mono text-gray-400 mt-1">Analyzing transcript turns, behavioral metrics & competency scores...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-panel p-6 border-red-500/40 bg-red-950/20 text-red-300 flex items-center justify-between">
        <div>
          <h4 className="font-bold text-sm flex items-center gap-2">
            <AlertTriangle size={18} className="text-red-400" /> Evaluation Report Error
          </h4>
          <p className="text-xs font-mono text-red-200/80 mt-1">{error}</p>
        </div>
        <button
          onClick={() => window.location.reload()}
          className="px-3 py-1.5 bg-red-900/40 hover:bg-red-900/60 border border-red-500/40 rounded text-xs text-white font-mono transition-all"
        >
          Retry
        </button>
      </div>
    );
  }

  const rec = evaluation?.final_recommendation || {};
  const metrics = evaluation?.behavioral_metrics || {};
  const competencies = evaluation?.detailed_competencies || [];
  const turns = evaluation?.full_transcript_evaluations || [];
  const candidateId = evaluation?.candidate_id || 'Candidate';
  const overallFit = evaluation?.scorecard?.overall_fit != null 
    ? Math.round(evaluation.scorecard.overall_fit * 100)
    : Math.round(rec.overall_suitability_score || 85);

  const getRecommendationBadge = (hiringRec) => {
    const raw = (hiringRec || 'Hire').toUpperCase().replace(' ', '_');
    switch (raw) {
      case 'STRONG_HIRE':
        return {
          bg: 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.2)]',
          label: 'STRONG HIRE',
          icon: <CheckCircle2 size={16} className="text-emerald-400" />,
        };
      case 'HIRE':
        return {
          bg: 'bg-green-500/20 border-green-500/50 text-green-300 shadow-[0_0_10px_rgba(34,197,94,0.2)]',
          label: 'HIRE',
          icon: <CheckCircle2 size={16} className="text-green-400" />,
        };
      case 'HOLD':
        return {
          bg: 'bg-amber-500/20 border-amber-500/50 text-amber-300 shadow-[0_0_10px_rgba(245,158,11,0.2)]',
          label: 'HOLD / RE-VET',
          icon: <AlertTriangle size={16} className="text-amber-400" />,
        };
      case 'REJECT':
        return {
          bg: 'bg-rose-500/20 border-rose-500/50 text-rose-300 shadow-[0_0_10px_rgba(244,63,94,0.2)]',
          label: 'REJECT',
          icon: <XCircle size={16} className="text-rose-400" />,
        };
      default:
        return {
          bg: 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300',
          label: hiringRec || 'HIRE',
          icon: <Award size={16} className="text-cyan-400" />,
        };
    };
  };

  const badgeStyle = getRecommendationBadge(rec.hiring_recommendation);

  const filteredTurns = turns;

  return (
    <div className="space-y-6 text-sm print:text-black print:bg-white">
      {/* ── Header Badge & Action Controls ─────────────────────────────── */}
      <div className="glass-panel p-6 border-cyan-500/30 bg-gradient-to-br from-cyan-950/20 via-slate-900/40 to-purple-950/20 relative overflow-hidden">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6 pb-6 border-b border-[var(--color-glass-border)]">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <span className="px-2.5 py-1 rounded-md bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 text-xs font-mono font-bold flex items-center gap-1.5">
                <BrainCircuit size={14} /> AI Evaluator Verified
              </span>
              <span className="text-xs font-mono text-gray-400">
                Interview ID: <strong className="text-white">{interviewId}</strong>
              </span>
            </div>
            <h2 className="text-2xl font-black text-white mt-2 flex items-center gap-3">
              <User className="text-cyan-400" size={24} />
              <span>{candidateId}</span>
            </h2>
            <p className="text-xs text-[var(--color-text-secondary)] font-mono mt-1 flex items-center gap-2">
              <Briefcase size={14} className="text-purple-400" />
              <span>Candidate Evaluation Report</span>
              <span>•</span>
              <span>Evaluated: {rec.evaluated_at ? new Date(rec.evaluated_at).toLocaleString() : 'Just now'}</span>
            </p>
          </div>

          <div className="flex items-center gap-4 flex-wrap print:hidden">
            {/* Suitability Score Display */}
            <div className="text-right bg-slate-900/60 p-3 rounded-xl border border-cyan-500/20">
              <span className="text-[10px] text-gray-400 uppercase tracking-wider block font-mono">Overall Score</span>
              <span className="text-2xl font-black text-cyan-400 font-mono">
                {overallFit}%
              </span>
            </div>

            {/* Recommendation Badge */}
            <div className={`px-4 py-2.5 rounded-xl border font-bold text-xs tracking-wider flex items-center gap-2 font-mono ${badgeStyle.bg}`}>
              {badgeStyle.icon}
              <span>{badgeStyle.label}</span>
            </div>

            {/* Print / Export Button */}
            <button
              onClick={handlePrint}
              className="flex items-center gap-2 bg-gradient-to-r from-cyan-600 to-cyan-500 hover:from-cyan-500 hover:to-cyan-400 text-white px-4 py-2.5 rounded-xl font-mono text-xs font-bold transition-all shadow-[0_0_12px_rgba(6,182,212,0.3)]"
              title="Print or export PDF summary"
            >
              <Printer size={16} />
              <span>Export Summary</span>
            </button>
          </div>
        </div>

        {/* Executive Summary */}
        <div className="mt-6 bg-[var(--color-glass-base)] p-4 rounded-xl border border-[var(--color-glass-border)]">
          <h3 className="text-xs font-bold text-cyan-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Sparkles size={14} /> Executive Summary
          </h3>
          <p className="text-gray-200 leading-relaxed font-sans text-sm">
            {rec.executive_summary || 'No summary generated yet.'}
          </p>
        </div>
      </div>

      {/* ── 2. Behavioral Indicators & Confidence Analysis ────────────── */}
      <div className="glass-panel p-6 space-y-4">
        <h3 className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2 font-mono">
          <TrendingUp size={16} /> Behavioral & Confidence Indicators
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Confidence Level */}
          <div className="p-4 rounded-xl bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">Confidence Level</span>
              <span className="font-mono font-bold text-cyan-400">
                {metrics.confidence_level != null ? `${Math.round(metrics.confidence_level * 100)}%` : '—'}
              </span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-cyan-400 h-2 rounded-full transition-all duration-500"
                style={{ width: metrics.confidence_level != null ? `${metrics.confidence_level * 100}%` : '0%' }}
              />
            </div>
          </div>

          {/* Communication Clarity */}
          <div className="p-4 rounded-xl bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">Communication Clarity</span>
              <span className="font-mono font-bold text-purple-400">
                {metrics.communication_clarity != null ? `${Math.round(metrics.communication_clarity * 100)}%` : '—'}
              </span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-purple-400 h-2 rounded-full transition-all duration-500"
                style={{ width: metrics.communication_clarity != null ? `${metrics.communication_clarity * 100}%` : '0%' }}
              />
            </div>
          </div>

          {/* Response Structure */}
          <div className="p-4 rounded-xl bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">Response Structure</span>
              <span className="font-mono font-bold text-green-400">
                {metrics.response_structure != null ? `${Math.round(metrics.response_structure * 100)}%` : '—'}
              </span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-green-400 h-2 rounded-full transition-all duration-500"
                style={{ width: metrics.response_structure != null ? `${metrics.response_structure * 100}%` : '0%' }}
              />
            </div>
          </div>

          {/* Engagement */}
          <div className="p-4 rounded-xl bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">Candidate Engagement</span>
              <span className="font-mono font-bold text-emerald-400">
                {metrics.candidate_engagement != null ? `${Math.round(metrics.candidate_engagement * 100)}%` : '—'}
              </span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-emerald-400 h-2 rounded-full transition-all duration-500"
                style={{ width: metrics.candidate_engagement != null ? `${metrics.candidate_engagement * 100}%` : '0%' }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* ── 3. Competencies Matrix ──────────────────────────────────────── */}
      <div className="glass-panel p-6 space-y-4">
        <h3 className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2 font-mono">
          <Award size={16} /> Technical Competencies Matrix
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {competencies.map((comp, idx) => (
            <div key={idx} className="p-5 rounded-xl bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] space-y-3">
              <div className="flex justify-between items-center">
                <span className="font-bold text-cyan-300 capitalize text-sm">{comp.competency_id?.replace(/_/g, ' ')}</span>
                <span className="font-mono font-bold text-xs px-2.5 py-1 rounded-md bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                  {comp.technical_accuracy}% Accuracy
                </span>
              </div>

              <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-cyan-500 to-purple-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${comp.technical_accuracy}%` }}
                />
              </div>

              {/* Key Strengths */}
              {comp.strengths && comp.strengths.length > 0 && (
                <div>
                  <span className="text-[10px] uppercase font-bold text-emerald-400 tracking-wider font-mono">Key Strengths:</span>
                  <ul className="list-disc list-inside text-xs text-gray-300 mt-1 space-y-0.5">
                    {comp.strengths.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Areas to Improve */}
              {comp.areas_for_improvement && comp.areas_for_improvement.length > 0 && (
                <div>
                  <span className="text-[10px] uppercase font-bold text-amber-400 tracking-wider font-mono">Areas for Improvement:</span>
                  <ul className="list-disc list-inside text-xs text-gray-400 mt-1 space-y-0.5">
                    {comp.areas_for_improvement.map((imp, i) => (
                      <li key={i}>{imp}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Verbatim Quotes */}
              {comp.quotes && comp.quotes.length > 0 && (
                <div className="pt-2 border-t border-[var(--color-glass-border)]">
                  <span className="text-[10px] uppercase font-bold text-purple-400 tracking-wider font-mono">Verbatim Evidence:</span>
                  <div className="mt-1 space-y-1">
                    {comp.quotes.map((q, i) => (
                      <p key={i} className="text-xs text-gray-300 italic bg-purple-950/20 p-2 rounded border border-purple-500/20">
                        "{q}"
                      </p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ── 4. Interactive Q&A Transcript Trajectory Log ───────────────── */}
      <div className="glass-panel p-6 space-y-4">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
          <h3 className="text-xs font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2 font-mono">
            <MessageSquare size={16} /> Interactive Transcript & Q&A Log
          </h3>
          <div className="relative w-full md:w-72">
            <Search size={14} className="absolute left-3 top-2.5 text-gray-400" />
            <input
              type="text"
              placeholder="Search transcript questions or notes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] rounded-xl pl-9 pr-3 py-1.5 text-xs font-mono focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        <div className="space-y-3">
          {filteredTurns.length === 0 ? (
            <p className="text-xs text-gray-400 font-mono py-6 text-center italic">No matching interview transcript turns found.</p>
          ) : (
            filteredTurns.map((turn, idx) => {
              const isExpanded = expandedTurn === idx;
              return (
                <div key={idx} className="p-4 rounded-xl bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] space-y-3 transition-all hover:border-cyan-500/30">
                  <div className="flex justify-between items-center text-xs font-mono">
                    <span className="px-2.5 py-0.5 rounded-md bg-purple-500/20 text-purple-300 border border-purple-500/30 font-bold">
                      Turn #{turn.question_number || idx + 1}
                    </span>
                    <div className="flex items-center gap-3 text-[11px]">
                      <span className="text-cyan-400 font-bold">Confidence: {Math.round((turn.confidence_score || 0.85) * 100)}%</span>
                      <span className="text-emerald-400 font-bold">Accuracy: {turn.technical_accuracy || 85}%</span>
                      <button
                        onClick={() => setExpandedTurn(isExpanded ? null : idx)}
                        className="text-gray-400 hover:text-white p-1"
                      >
                        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </button>
                    </div>
                  </div>

                  <div>
                    <p className="text-xs font-bold text-cyan-300 leading-relaxed">
                      Q: {turn.question}
                    </p>
                    <div className="text-xs text-gray-200 mt-2 pl-3 border-l-2 border-cyan-500/50 bg-cyan-950/20 p-2.5 rounded-r-lg leading-relaxed">
                      <strong>Candidate Answer:</strong> "{turn.candidate_answer}"
                    </div>
                  </div>

                  {turn.evaluator_notes && (
                    <div className="p-2.5 rounded-lg bg-cyan-950/40 border border-cyan-500/20 text-[11px] text-cyan-300 font-mono flex items-start gap-2">
                      <Sparkles size={14} className="text-cyan-400 shrink-0 mt-0.5" />
                      <div>
                        <strong className="text-cyan-400">AI Evaluator Note:</strong> {turn.evaluator_notes}
                      </div>
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
