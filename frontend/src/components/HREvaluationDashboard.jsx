import React, { useState, useEffect } from 'react';
import { Loader2, Clock, AlertCircle, ChevronDown } from 'lucide-react';
import HRDebriefCard from './HRDebriefCard';
import EvaluationReport from './EvaluationReport';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

export default function HREvaluationDashboard({ interviewId = 'iv-alex' }) {
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isPending, setIsPending] = useState(false);
  const [debriefOpen, setDebriefOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    let attempts = 0;
    const MAX_ATTEMPTS = 15;

    async function fetchEvaluation() {
      if (attempts >= MAX_ATTEMPTS) {
        if (isMounted) {
          setError('Evaluation is taking too long to generate. Please try again later.');
          setLoading(false);
          setIsPending(false);
        }
        return;
      }

      attempts++;
      try {
        const res = await fetch(`${API_BASE}/api/interviews/${interviewId}/evaluation`, {
          headers: {
            'Content-Type': 'application/json',
            'X-User-Role': 'hr',
          },
        });

        if (res.status === 404) {
          if (isMounted) {
            setIsPending(true);
            setLoading(false);
            setTimeout(fetchEvaluation, 5000);
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
          setIsPending(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || 'Error loading evaluation report');
          setLoading(false);
          setIsPending(false);
        }
      }
    }

    if (interviewId) {
      fetchEvaluation();
    }
    return () => { isMounted = false; };
  }, [interviewId]);

  /* ── Loading state ── */
  if (loading) {
    return (
      <div className="card">
        <div className="card-body py-16 flex flex-col items-center justify-center gap-3">
          <Loader2 className="size-8 text-cyan-400 animate-spin" />
          <p className="text-sm text-white/50">Loading evaluation report…</p>
        </div>
      </div>
    );
  }

  /* ── Pending / generating state ── */
  if (isPending) {
    return (
      <div className="card">
        <div className="card-body py-16 flex flex-col items-center justify-center gap-3 animate-pulse">
          <Clock className="size-8 text-amber-400" />
          <p className="text-sm text-white/50">
            Generating evaluation… This may take a moment.
          </p>
        </div>
      </div>
    );
  }

  /* ── Error state ── */
  if (error) {
    return (
      <div className="card border-rose-400/20">
        <div className="card-body py-12 flex flex-col items-center justify-center gap-4">
          <AlertCircle className="size-8 text-rose-400" />
          <p className="text-sm text-rose-300 text-center max-w-md">{error}</p>
          <button
            className="btn btn-sm mt-1"
            onClick={() => window.location.reload()}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  /* ── Data loaded ── */
  return (
    <div className="space-y-6">
      {/* Collapsible HR Debrief Card */}
      <div className="card">
        <button
          type="button"
          className="card-body flex items-center justify-between w-full text-left"
          onClick={() => setDebriefOpen((o) => !o)}
        >
          <span className="text-sm font-medium text-white/70">HR Debrief</span>
          <ChevronDown
            className={`size-4 text-white/40 transition-transform duration-200 ${
              debriefOpen ? 'rotate-180' : ''
            }`}
          />
        </button>

        {debriefOpen && (
          <div className="px-5 pb-5">
            <HRDebriefCard
              interviewId={interviewId}
              candidateId={evaluation?.candidate_id || 'c-candidate'}
            />
          </div>
        )}
      </div>

      {/* Evaluation Report */}
      <EvaluationReport interviewId={interviewId} initialData={evaluation} />
    </div>
  );
}
