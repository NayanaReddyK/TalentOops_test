import React, { useState, useEffect } from 'react';
import { History, Users, ArrowRight, Loader2, AlertCircle } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

export default function CandidateHistory({ onViewReport }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(`${API_BASE}/api/history`);
        if (!response.ok) {
          throw new Error('Failed to fetch candidate history');
        }
        const data = await response.json();
        setHistory(data);
      } catch (err) {
        setError(err.message || 'An error occurred while fetching data');
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  const getScoreColor = (score) => {
    if (!score) return 'text-gray-400';
    if (score >= 80) return 'text-emerald-400';
    if (score >= 60) return 'text-amber-400';
    return 'text-rose-400';
  };

  const getRecommendationBadge = (recommendation) => {
    const rec = recommendation?.toLowerCase() || '';
    if (rec.includes('strong') || rec.includes('hire')) {
      return 'badge bg-emerald-400/10 text-emerald-400 border-emerald-400/20';
    }
    if (rec.includes('no') || rec.includes('reject')) {
      return 'badge bg-rose-400/10 text-rose-400 border-rose-400/20';
    }
    return 'badge bg-amber-400/10 text-amber-400 border-amber-400/20';
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-gray-400 space-y-4">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
        <p>Loading candidate history...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card border-rose-500/30 bg-rose-500/5 p-6 flex flex-col items-center justify-center text-center space-y-4">
        <AlertCircle className="w-10 h-10 text-rose-400" />
        <div className="text-rose-400 font-medium">{error}</div>
        <button className="btn btn-outline" onClick={() => window.location.reload()}>
          Try Again
        </button>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="card p-12 flex flex-col items-center justify-center text-center space-y-4">
        <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-2">
          <History className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-xl font-medium text-gray-200">No History Found</h3>
        <p className="text-gray-400 max-w-md">
          There are no candidate records available yet. Start an interview to see history here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 mb-6">
        <Users className="w-6 h-6 text-cyan-400" />
        <h2 className="text-2xl font-semibold text-gray-100">Candidate History</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {history.map((item, index) => (
          <div key={item.interview_id || index} className="card p-5 flex flex-col hover:border-white/10 transition-colors">
            <div className="flex justify-between items-start mb-4 gap-2">
              <div className="min-w-0">
                <h3 className="text-lg font-medium text-gray-100 truncate">{item.candidate_name || 'Unknown Candidate'}</h3>
                <p className="text-sm text-gray-400 truncate">{item.email || 'No email provided'}</p>
              </div>
              {item.status && (
                <span className="badge shrink-0">
                  {item.status}
                </span>
              )}
            </div>

            <div className="space-y-3 mb-6 flex-grow">
              <div className="flex justify-between items-center bg-black/20 rounded p-3">
                <span className="text-sm text-gray-400">Overall Score</span>
                <span className={`text-xl font-bold font-mono ${getScoreColor(item.overall_score)}`}>
                  {item.overall_score ? `${item.overall_score}%` : 'N/A'}
                </span>
              </div>
              
              {item.recommendation && (
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm text-gray-400">Recommendation</span>
                  <span className={getRecommendationBadge(item.recommendation)}>
                    {item.recommendation}
                  </span>
                </div>
              )}
            </div>

            <button
              onClick={() => onViewReport(item.interview_id)}
              className="btn btn-primary w-full flex items-center justify-center group mt-auto"
            >
              <span>View Report</span>
              <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
