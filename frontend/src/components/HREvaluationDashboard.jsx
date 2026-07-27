import React, { useState, useEffect } from 'react';
import HRDebriefCard from './HRDebriefCard';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export default function HREvaluationDashboard({ interviewId = 'iv-alex' }) {
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    let isMounted = true;
    async function fetchEvaluation() {
      setLoading(true);
      setError('');
      try {
        const res = await fetch(`${API_BASE}/api/interviews/${interviewId}/evaluation`, {
          headers: {
            'Content-Type': 'application/json',
            'X-User-Role': 'hr',
          },
        });
        if (!res.ok) {
          throw new Error(`Failed to fetch evaluation: ${res.statusText}`);
        }
        const data = await res.json();
        if (isMounted) {
          setEvaluation(data);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || 'Error loading evaluation report');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    if (interviewId) {
      fetchEvaluation();
    }
  }, [interviewId]);

  if (loading) {
    return (
      <div className="glass-panel p-8 text-center text-cyan-400 font-mono animate-pulse">
        ⚡ Loading HR Candidate Evaluation Report...
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-panel p-6 border-red-500/50 bg-red-950/30 text-red-300">
        <h3 className="font-bold mb-2">⚠️ Error Loading HR Evaluation</h3>
        <p className="text-sm font-mono">{error}</p>
      </div>
    );
  }

  const rec = evaluation?.final_recommendation || {};
  const metrics = evaluation?.behavioral_metrics || {};
  const competencies = evaluation?.detailed_competencies || [];
  const turns = evaluation?.full_transcript_evaluations || [];

  // Filter turns by search query
  const filteredTurns = turns.filter(
    (t) =>
      t.question?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.candidate_answer?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.evaluator_notes?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getRecommendationBadge = (recommendation) => {
    switch (recommendation) {
      case 'Strong Hire':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50';
      case 'Hire':
        return 'bg-green-500/20 text-green-300 border-green-500/50';
      case 'Hold':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/50';
      case 'Reject':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/50';
      default:
        return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50';
    }
  };

  return (
    <div className="space-y-6 text-sm">
      {/* Realtime HR Debrief Notification Card */}
      <HRDebriefCard interviewId={interviewId} candidateId={evaluation?.candidate_id || 'c-alex'} />

      {/* 1. Header & Executive Summary Card */}
      <div className="glass-panel p-6 border-cyan-500/30 bg-gradient-to-br from-cyan-950/20 to-purple-950/20">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4 pb-4 border-b border-[var(--color-glass-border)]">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-cyan-300">📊 Candidate Evaluation Report</h2>
              <span className="text-xs font-mono px-2 py-1 rounded bg-cyan-900/40 text-cyan-400 border border-cyan-500/30">
                {interviewId}
              </span>
            </div>
            <p className="text-xs text-[var(--color-text-secondary)] mt-1 font-mono">
              Candidate ID: {evaluation?.candidate_id || 'Unknown'} | Evaluated: {rec.evaluated_at ? new Date(rec.evaluated_at).toLocaleString() : 'Just now'}
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Suitability Score Pill */}
            <div className="text-right">
              <span className="text-[10px] text-gray-400 uppercase tracking-wider block font-mono">Suitability</span>
              <span className="text-2xl font-black text-cyan-400 font-mono">
                {rec.overall_suitability_score != null ? `${rec.overall_suitability_score}%` : '85.0%'}
              </span>
            </div>

            {/* Recommendation Badge */}
            <div className={`px-4 py-2 rounded-lg border font-bold text-sm shadow-md font-mono ${getRecommendationBadge(rec.hiring_recommendation)}`}>
              {rec.hiring_recommendation || 'Hire'}
            </div>
          </div>
        </div>

        {/* Executive Summary */}
        <div className="bg-[var(--color-glass-base)] p-4 rounded-lg border border-[var(--color-glass-border)]">
          <h3 className="text-xs font-bold text-cyan-400 uppercase tracking-wider mb-2">Executive Summary</h3>
          <p className="text-gray-200 leading-relaxed font-sans text-sm">
            {rec.executive_summary || 'No summary available.'}
          </p>
        </div>
      </div>

      {/* 2. Behavioral & Confidence Metrics */}
      <div className="glass-panel p-6 space-y-4">
        <h3 className="text-sm font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
          <span>🧠</span> Behavioral & Confidence Analysis
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Metric 1 */}
          <div className="p-4 rounded-lg bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">Confidence Level</span>
              <span className="font-mono font-bold text-cyan-400">
                {metrics.confidence_level != null ? `${Math.round(metrics.confidence_level * 100)}%` : '88%'}
              </span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-cyan-400 h-2 rounded-full transition-all duration-500"
                style={{ width: `${(metrics.confidence_level || 0.88) * 100}%` }}
              />
            </div>
          </div>

          {/* Metric 2 */}
          <div className="p-4 rounded-lg bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">Communication Clarity</span>
              <span className="font-mono font-bold text-purple-400">
                {metrics.communication_clarity != null ? `${Math.round(metrics.communication_clarity * 100)}%` : '85%'}
              </span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-purple-400 h-2 rounded-full transition-all duration-500"
                style={{ width: `${(metrics.communication_clarity || 0.85) * 100}%` }}
              />
            </div>
          </div>

          {/* Metric 3 */}
          <div className="p-4 rounded-lg bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">Response Structure</span>
              <span className="font-mono font-bold text-green-400">
                {metrics.response_structure != null ? `${Math.round(metrics.response_structure * 100)}%` : '82%'}
              </span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-green-400 h-2 rounded-full transition-all duration-500"
                style={{ width: `${(metrics.response_structure || 0.82) * 100}%` }}
              />
            </div>
          </div>

          {/* Metric 4 */}
          <div className="p-4 rounded-lg bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">Engagement</span>
              <span className="font-mono font-bold text-emerald-400">
                {metrics.candidate_engagement != null ? `${Math.round(metrics.candidate_engagement * 100)}%` : '90%'}
              </span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-emerald-400 h-2 rounded-full transition-all duration-500"
                style={{ width: `${(metrics.candidate_engagement || 0.90) * 100}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* 3. Technical Competency Matrix */}
      <div className="glass-panel p-6 space-y-4">
        <h3 className="text-sm font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
          <span>🛠️</span> Technical Competency Matrix
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {competencies.map((comp, idx) => (
            <div key={idx} className="p-4 rounded-lg bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] space-y-3">
              <div className="flex justify-between items-center">
                <span className="font-bold text-cyan-300 capitalize">{comp.competency_id?.replace('_', ' ')}</span>
                <span className="font-mono font-bold text-xs px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-400">
                  {comp.technical_accuracy}% Accuracy
                </span>
              </div>

              <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-cyan-500 to-purple-500 h-2 rounded-full"
                  style={{ width: `${comp.technical_accuracy}%` }}
                />
              </div>

              {/* Strengths */}
              {comp.strengths && comp.strengths.length > 0 && (
                <div>
                  <span className="text-[10px] uppercase font-bold text-emerald-400 tracking-wider">Key Strengths:</span>
                  <ul className="list-disc list-inside text-xs text-gray-300 mt-1 space-y-0.5">
                    {comp.strengths.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Improvements */}
              {comp.areas_for_improvement && comp.areas_for_improvement.length > 0 && (
                <div>
                  <span className="text-[10px] uppercase font-bold text-amber-400 tracking-wider">Areas to Improve:</span>
                  <ul className="list-disc list-inside text-xs text-gray-400 mt-1 space-y-0.5">
                    {comp.areas_for_improvement.map((imp, i) => (
                      <li key={i}>{imp}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 4. Interactive Transcript View */}
      <div className="glass-panel p-6 space-y-4">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
          <h3 className="text-sm font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-2">
            <span>💬</span> Q&A Evaluation Trajectory
          </h3>
          <input
            type="text"
            placeholder="Search transcript questions or answers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full md:w-64 bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] rounded-md px-3 py-1.5 text-xs focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div className="space-y-4">
          {filteredTurns.length === 0 ? (
            <p className="text-xs text-gray-400 font-mono py-4 text-center">No matching interview turns found.</p>
          ) : (
            filteredTurns.map((turn, idx) => (
              <div key={idx} className="p-4 rounded-lg bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] space-y-2">
                <div className="flex justify-between items-center text-xs font-mono">
                  <span className="px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-bold">
                    Turn #{turn.question_number || idx + 1}
                  </span>
                  <div className="flex gap-3 text-[11px]">
                    <span className="text-cyan-400">Confidence: {Math.round((turn.confidence_score || 0.85) * 100)}%</span>
                    <span className="text-green-400">Accuracy: {turn.technical_accuracy || 85}%</span>
                  </div>
                </div>

                <div>
                  <p className="text-xs font-bold text-cyan-300">Q: {turn.question}</p>
                  <p className="text-xs text-gray-200 mt-1 pl-3 border-l-2 border-cyan-500/50">
                    {turn.candidate_answer}
                  </p>
                </div>

                {turn.evaluator_notes && (
                  <div className="p-2 rounded bg-cyan-950/30 border border-cyan-500/20 text-[11px] text-cyan-300 font-mono">
                    💡 <span className="font-bold">AI Evaluator Note:</span> {turn.evaluator_notes}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
