import React, { useState } from 'react';
import { Video, Loader2, PhoneOff, Copy, ExternalLink } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

export default function DeployBot({ roleId, candidateId, interviewId, onDeployed, onEnded }) {
  const [roomId,   setRoomId]   = useState('');
  const [roomUrl,  setRoomUrl]  = useState('');
  const [creating, setCreating] = useState(false);
  const [ending,   setEnding]   = useState(false);
  const [copied,   setCopied]   = useState(false);
  const [error,    setError]    = useState(null);

  const handleCreate = async () => {
    setCreating(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/interviews/deploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_id: candidateId,
          role_id:      roleId,
          interview_id: interviewId || undefined,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || res.statusText);
      }
      const data = await res.json();
      setRoomId(data.room_id);
      setRoomUrl(data.room_url);
      if (data.interview_id && onDeployed) onDeployed(data.interview_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleEnd = async () => {
    setEnding(true);
    setError(null);
    try {
      await fetch(`${API_BASE}/rooms/${roomId}/end`, { method: 'POST' });
      setRoomId('');
      setRoomUrl('');
      if (onEnded) onEnded();
    } catch (err) {
      setError(err.message);
    } finally {
      setEnding(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(roomUrl).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="flex items-center gap-3 flex-wrap">
      {!roomId ? (
        <button
          onClick={handleCreate}
          disabled={creating}
          className="btn btn-primary"
        >
          {creating ? <Loader2 size={16} className="animate-spin" /> : <Video size={16} />}
          Create Interview Room
        </button>
      ) : (
        <>
          <span
            className="badge bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 truncate max-w-[240px]"
            title={roomUrl}
          >
            {roomUrl}
          </span>

          <button onClick={handleCopy} className="btn btn-secondary btn-sm">
            <Copy size={14} />
            {copied ? 'Copied!' : 'Copy'}
          </button>

          <a
            href={roomUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary btn-sm"
          >
            <ExternalLink size={14} />
            Open
          </a>

          <button
            onClick={handleEnd}
            disabled={ending}
            className="btn btn-ghost btn-sm text-rose-400 hover:text-rose-300 hover:bg-rose-500/10"
          >
            {ending ? <Loader2 size={14} className="animate-spin" /> : <PhoneOff size={14} />}
            End & Evaluate
          </button>
        </>
      )}

      {error && <span className="text-rose-400 text-xs">{error}</span>}
    </div>
  );
}
