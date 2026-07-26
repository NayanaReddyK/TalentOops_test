import React, { useState } from 'react';
import { Rocket, Loader2, LogOut } from 'lucide-react';

export default function DeployBot({ roleId, candidateId, interviewId, onDeployed }) {
  const [meetUrl, setMeetUrl] = useState('');
  const [activeMeetUrl, setActiveMeetUrl] = useState('');
  const [deploying, setDeploying] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [error, setError] = useState(null);

  const handleStop = async () => {
    const targetUrl = activeMeetUrl || meetUrl;
    if (!targetUrl) {
      setError('Enter a Meet URL to stop the bot.');
      return;
    }
    setStopping(true);
    setError(null);
    try {
      const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
      const res = await fetch(`${apiBase}/interviews/stop_by_url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ meet_url: targetUrl })
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(`Failed to stop bot: ${errorData.detail || res.statusText}`);
      }
      if (activeMeetUrl) setActiveMeetUrl('');
    } catch (err) {
      setError(err.message);
    } finally {
      setStopping(false);
    }
  };

  const handleDeploy = async () => {
    if (!meetUrl) {
      setError('Meet URL is required');
      return;
    }

    setDeploying(true);
    setError(null);

    try {
      const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
      const res = await fetch(`${apiBase}/interviews/deploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          meet_url: meetUrl,
          candidate_id: candidateId,
          role_id: roleId,
          interview_id: interviewId
        })
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        const message = errorData.detail || res.statusText;
        throw new Error(`Failed to deploy bot: ${message}`);
      }

      const data = await res.json();
      if (data.interview_id && onDeployed) {
        onDeployed(data.interview_id);
      }
      setActiveMeetUrl(meetUrl);
      setMeetUrl('');
    } catch (err) {
      setError(err.message);
    } finally {
      setDeploying(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <input 
        type="text" 
        value={meetUrl} 
        onChange={(e) => setMeetUrl(e.target.value)} 
        placeholder="https://meet.google.com/xyz"
        className="bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] rounded-md px-4 py-2 font-mono text-sm focus:outline-none focus:border-cyan-500 w-64"
        disabled={deploying}
      />
      <button 
        onClick={handleDeploy}
        disabled={deploying || !meetUrl}
        className="flex items-center gap-2 bg-gradient-to-r from-cyan-600 to-cyan-500 hover:from-cyan-500 hover:to-cyan-400 text-white px-4 py-2 rounded-md font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(6,182,212,0.4)]"
      >
        {deploying ? <Loader2 size={16} className="animate-spin" /> : <Rocket size={16} />}
        Deploy Bot
      </button>
      
      {(activeMeetUrl || meetUrl) && (
        <button 
          onClick={handleStop}
          disabled={stopping}
          className="flex items-center gap-2 bg-[var(--color-glass-base)] border border-rose-500/50 hover:bg-rose-500/20 text-rose-400 px-4 py-2 rounded-md font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          title="End Interview and Kick Bot"
        >
          {stopping ? <Loader2 size={16} className="animate-spin" /> : <LogOut size={16} />}
          End
        </button>
      )}
      {error && <span className="text-rose-500 text-sm ml-2">{error}</span>}
    </div>
  );
}
