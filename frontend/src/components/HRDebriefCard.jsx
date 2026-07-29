import React, { useState, useEffect, useRef } from 'react';
import { MessageCircle, Send, Mic, ExternalLink, Loader2 } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

export default function HRDebriefCard({ interviewId = 'iv-alex', candidateId = 'c1' }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hrQuestion, setHrQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const [qaHistory, setQaHistory] = useState([]);
  const [audioUrl, setAudioUrl] = useState('');
  const scrollRef = useRef(null);

  /* ── Fetch debrief session ─────────────────────────────────────────── */
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
          if (isMounted) setSession(data);
        }
      } catch (err) {
        console.error('Error fetching HR debrief session:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    if (interviewId) fetchDebrief();
    return () => { isMounted = false; };
  }, [interviewId]);

  /* ── Auto-scroll on new messages ───────────────────────────────────── */
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [qaHistory, asking]);

  /* ── Send a question ───────────────────────────────────────────────── */
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
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
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
          response: `Unable to reach the Manager Agent — ${err.message}`,
          isError: true,
        },
      ]);
    } finally {
      setAsking(false);
    }
  };

  /* ── Loading state ─────────────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="card animate-fade-in">
        <div className="card-body flex items-center justify-center gap-3 py-12">
          <Loader2 size={18} className="text-purple animate-spin" />
          <span className="text-sm text-[var(--color-text-secondary)]">
            Connecting to Manager Agent…
          </span>
        </div>
      </div>
    );
  }

  const roomUrl =
    session?.room_url ||
    `http://localhost:8000/interview/debrief-${interviewId.slice(0, 8)}`;

  /* ── Render ────────────────────────────────────────────────────────── */
  return (
    <div className="card flex flex-col animate-fade-in" style={{ height: 520 }}>
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="card-header">
        <div className="flex items-center gap-3 min-w-0">
          <div className="shrink-0 w-9 h-9 rounded-xl bg-purple-muted flex items-center justify-center">
            <MessageCircle size={18} className="text-purple" />
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] leading-tight">
              Ask the AI Manager
            </h3>
            <p className="text-xs text-[var(--color-text-secondary)] truncate">
              Chat with the Manager AI Agent about the candidate evaluation
            </p>
          </div>
        </div>

        {/* Voice session link */}
        <a
          href={roomUrl}
          target="_blank"
          rel="noreferrer"
          className="btn btn-ghost btn-sm shrink-0 gap-1.5 text-purple hover:text-[var(--color-text-primary)]"
        >
          <ExternalLink size={13} />
          <span className="hidden sm:inline">Join voice session</span>
        </a>
      </div>

      {/* ── Chat area ───────────────────────────────────────────────── */}
      <div
        ref={scrollRef}
        className="card-body flex-1 overflow-y-auto space-y-4"
        style={{ paddingBottom: 8 }}
      >
        {/* Empty state */}
        {qaHistory.length === 0 && !asking && (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-center opacity-60">
            <MessageCircle size={28} className="text-[var(--color-text-muted)]" />
            <p className="text-xs text-[var(--color-text-muted)] max-w-[240px]">
              Ask a question about the candidate's interview performance to get started.
            </p>
          </div>
        )}

        {/* Messages */}
        {qaHistory.map((item, idx) => (
          <div key={idx} className="space-y-3 animate-fade-in">
            {/* HR question — right side */}
            <div className="flex justify-end">
              <div
                className="max-w-[75%] rounded-2xl rounded-br-md px-4 py-2.5 text-sm leading-relaxed"
                style={{ background: 'var(--color-accent-muted)', color: 'var(--color-accent)' }}
              >
                {item.question}
              </div>
            </div>

            {/* AI response — left side */}
            <div className="flex justify-start gap-2.5">
              <div className="shrink-0 w-7 h-7 rounded-lg bg-purple-muted flex items-center justify-center mt-0.5">
                <MessageCircle size={13} className="text-purple" />
              </div>
              <div className="max-w-[75%] space-y-2">
                <div
                  className={`rounded-2xl rounded-tl-md px-4 py-2.5 text-sm leading-relaxed ${
                    item.isError
                      ? 'bg-rose-muted text-rose'
                      : 'bg-[var(--color-glass-hover)] text-[var(--color-text-primary)]'
                  }`}
                >
                  {item.response}
                </div>

                {/* Inline audio */}
                {item.audio_b64 && (
                  <div className="flex items-center gap-2 pl-1">
                    <Mic size={13} className="text-purple shrink-0" />
                    <audio
                      controls
                      src={`data:audio/wav;base64,${item.audio_b64}`}
                      className="h-7 w-52"
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {asking && (
          <div className="flex justify-start gap-2.5 animate-fade-in">
            <div className="shrink-0 w-7 h-7 rounded-lg bg-purple-muted flex items-center justify-center mt-0.5">
              <MessageCircle size={13} className="text-purple" />
            </div>
            <div className="rounded-2xl rounded-tl-md px-4 py-3 bg-[var(--color-glass-hover)] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-text-muted)] animate-pulse-soft" />
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-text-muted)] animate-pulse-soft" style={{ animationDelay: '0.2s' }} />
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-text-muted)] animate-pulse-soft" style={{ animationDelay: '0.4s' }} />
            </div>
          </div>
        )}

        {/* Global audio player for latest response */}
        {audioUrl && (
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-purple-muted mt-2">
            <Mic size={14} className="text-purple shrink-0" />
            <span className="text-xs text-purple font-medium">Latest audio</span>
            <audio controls autoPlay src={audioUrl} className="h-7 flex-1 min-w-0" />
          </div>
        )}
      </div>

      {/* ── Input bar ───────────────────────────────────────────────── */}
      <div className="px-4 pb-4 pt-2 border-t border-[var(--color-glass-border)]">
        <form onSubmit={handleAskManager} className="flex items-center gap-2">
          <input
            type="text"
            value={hrQuestion}
            onChange={(e) => setHrQuestion(e.target.value)}
            placeholder="Ask about the candidate…"
            className="input flex-1"
            style={{ borderRadius: 12 }}
          />
          <button
            type="submit"
            disabled={asking || !hrQuestion.trim()}
            className="btn btn-primary shrink-0"
            style={{ padding: '10px 14px', borderRadius: 12 }}
          >
            {asking ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Send size={16} />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
