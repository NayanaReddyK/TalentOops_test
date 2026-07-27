import React, { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export default function HRDebriefCard({ interviewId = 'iv-alex', candidateId = 'c1' }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hrQuestion, setHrQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const [qaHistory, setQaHistory] = useState([]);
  const [audioUrl, setAudioUrl] = useState('');

  useEffect(() => {
    let isMounted = true;
    async function fetchDebrief() {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/debrief/${interviewId}`, {
          headers: {
            'Content-Type': 'application/json',
            'X-User-Role': 'hr',
          },
        });
        if (res.ok) {
          const data = await res.json();
          if (isMounted) {
            setSession(data);
          }
        }
      } catch (err) {
        console.error('Error fetching HR debrief session:', err);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    if (interviewId) {
      fetchDebrief();
    }
  }, [interviewId]);

  const handleAskManager = async (e) => {
    e.preventDefault();
    if (!hrQuestion.trim() || asking) return;

    const currentQ = hrQuestion;
    setHrQuestion('');
    setAsking(true);

    try {
      const res = await fetch(`${API_BASE}/api/debrief/turn`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          interview_id: interviewId,
          hr_question: currentQ,
        }),
      });
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const data = await res.json();

      setQaHistory((prev) => [
        ...prev,
        {
          question: currentQ,
          response: data.response_text,
          audio_b64: data.audio_b64,
        },
      ]);

      if (data.audio_b64) {
        setAudioUrl(`data:audio/wav;base64,${data.audio_b64}`);
      }
    } catch (err) {
      console.error('Error asking Manager Agent:', err);
      setQaHistory((prev) => [
        ...prev,
        {
          question: currentQ,
          response: `Error: Unable to connect to Manager Agent (${err.message})`,
        },
      ]);
    } finally {
      setAsking(false);
    }
  };

  if (loading) {
    return (
      <div className="glass-panel p-4 text-center text-xs font-mono text-purple-400 animate-pulse">
        ⚡ Checking Manager Agent HR Debrief Session status...
      </div>
    );
  }

  const roomUrl = session?.room_url || `http://localhost:8000/interview/debrief-${interviewId.slice(0, 8)}`;
  const status = session?.status || 'Manager Agent Waiting';

  return (
    <div className="glass-panel p-6 border-purple-500/40 bg-gradient-to-r from-purple-950/30 to-cyan-950/30 space-y-4">
      {/* 1. Realtime Debrief Notification Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-purple-500/30 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">🎙️</span>
            <h3 className="text-base font-bold text-purple-300">
              HR Debrief Session Ready for Candidate #{session?.candidate_id || candidateId}
            </h3>
          </div>
          <p className="text-xs text-gray-300 mt-1 font-mono">
            Join the live TalentOops Interview Room to verbally debrief with the AI Manager Agent using complete interview transcript RAG context.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="px-3 py-1 rounded font-mono font-bold text-xs bg-purple-500/20 text-purple-300 border border-purple-500/40 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-purple-400 animate-ping" />
            {status}
          </span>

          <a
            href={roomUrl}
            target="_blank"
            rel="noreferrer"
            className="px-4 py-2 bg-gradient-to-r from-purple-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500 text-white font-bold text-xs rounded-lg shadow-lg shadow-purple-500/20 transition-all flex items-center gap-1.5"
          >
            <span>🎙️</span> Join Debrief Room
          </a>
        </div>
      </div>

      {/* 2. Interactive Manager Agent HR Q&A Console */}
      <div className="space-y-3 pt-2">
        <h4 className="text-xs font-bold text-purple-300 uppercase tracking-wider flex items-center gap-2">
          <span>🧠</span> Ask Manager Agent Oral HR Questions (Transcript RAG)
        </h4>

        <form onSubmit={handleAskManager} className="flex gap-2">
          <input
            type="text"
            value={hrQuestion}
            onChange={(e) => setHrQuestion(e.target.value)}
            placeholder="Ask Manager Agent (e.g. 'Why did they get a high rating on database architecture?')..."
            className="flex-1 bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] rounded-md px-3 py-2 text-xs focus:outline-none focus:border-purple-500 font-sans"
          />
          <button
            type="submit"
            disabled={asking || !hrQuestion.trim()}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white font-bold text-xs rounded-md shadow transition-all disabled:opacity-50"
          >
            {asking ? '⚡ Thinking...' : 'Ask Manager'}
          </button>
        </form>

        {/* Audio Player */}
        {audioUrl && (
          <div className="p-3 rounded bg-purple-950/40 border border-purple-500/30 flex items-center justify-between gap-3 text-xs">
            <span className="font-mono text-purple-300 flex items-center gap-1">
              <span>🔊</span> Manager Agent Audio Response:
            </span>
            <audio controls autoPlay src={audioUrl} className="h-8 w-64" />
          </div>
        )}

        {/* Q&A History Log */}
        {qaHistory.length > 0 && (
          <div className="space-y-2 mt-3 max-h-60 overflow-y-auto pr-1">
            {qaHistory.map((item, idx) => (
              <div key={idx} className="p-3 rounded-lg bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] text-xs space-y-1">
                <p className="font-bold text-purple-300">HR Query: {item.question}</p>
                <p className="text-gray-200 pl-3 border-l-2 border-purple-500/50 leading-relaxed">
                  🤖 <span className="font-bold text-cyan-300">Manager Agent:</span> {item.response}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
