import React, { useState, useEffect } from 'react';
import HRDebriefCard from './HRDebriefCard';
import EvaluationReport from './EvaluationReport';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export default function HREvaluationDashboard({ interviewId = 'iv-alex' }) {
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isPending, setIsPending] = useState(false);

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

  if (loading) {
    return (
      <div className="glass-panel p-10 text-center text-cyan-400 font-mono animate-pulse">
        ⚡ Loading HR Candidate Evaluation Report...
      </div>
    );
  }

  if (isPending) {
    return (
      <div className="glass-panel p-10 text-center text-amber-400 font-mono animate-pulse">
        ⏳ Evaluation is still being processed... Retrying automatically.
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

  return (
    <div className="space-y-6">
      {/* Realtime HR Debrief Notification Card */}
      <HRDebriefCard interviewId={interviewId} candidateId={evaluation?.candidate_id || 'c-candidate'} />

      {/* Polish Candidate Evaluation Report Component */}
      <EvaluationReport interviewId={interviewId} initialData={evaluation} />
    </div>
  );
}
