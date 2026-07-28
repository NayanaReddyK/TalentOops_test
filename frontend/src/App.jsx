import React, { useState } from 'react';
import { createClient } from '@supabase/supabase-js';
import DeployBot from './components/DeployBot';
import TranscriptStream from './components/TranscriptStream';
import FairnessHeatmap from './components/FairnessHeatmap';
import ScorecardView from './components/ScorecardView';
import UploadZone from './components/UploadZone';
import PipelineVisualizer from './components/PipelineVisualizer';
import HREvaluationDashboard from './components/HREvaluationDashboard';
import InterviewRoom from './components/InterviewRoom';

// Initialize Supabase Client
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://qzthddhmxdcocikdhumh.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF6dGhkZGhteGRjb2Npa2RodW1oIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQxNjc4MjAsImV4cCI6MjA5OTc0MzgyMH0.VJbR0Ad8t9SgsAPc9XyFM3bkLrPocmEekjOnnPwoJss';
const supabase = supabaseUrl && supabaseAnonKey ? createClient(supabaseUrl, supabaseAnonKey) : null;
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

function App() {
  // ── Interview Room route: /interview/{room_id} renders full-screen room ──
  const pathMatch = window.location.pathname.match(/^\/interview\/([\w-]+)/);
  if (pathMatch) {
    return <InterviewRoom roomId={pathMatch[1]} />;
  }

  const urlParams = new URLSearchParams(window.location.search);
  const [roleId] = useState(urlParams.get('roleId') || 'r1');
  const [candidateId] = useState(urlParams.get('candidateId') || 'c1');
  const [interviewId, setInterviewId] = useState(urlParams.get('interviewId') || 'iv-alex');
  const [activeTab, setActiveTab] = useState(urlParams.get('tab') || 'live'); // 'live' | 'hr'

  // Pipeline execution state
  const [goal, setGoal] = useState('Hire a Senior Backend Engineer (Python, FastAPI, Postgres)');
  const [standard, setStandard] = useState('Candidate must demonstrate strong experience with async Python, distributed systems, and SQL optimization');
  const [selectedFile, setSelectedFile] = useState(null);
  const [running, setRunning] = useState(false);
  const [activeNode, setActiveNode] = useState('');
  const [completedNodes, setCompletedNodes] = useState([]);
  const [runResult, setRunResult] = useState(null);
  const [debriefDeployed, setDebriefDeployed] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleRunPipeline = async () => {
    setRunning(true);
    setActiveNode('sourcing');
    setCompletedNodes([]);
    setRunResult(null);
    setDebriefDeployed(false);
    setErrorMessage('');

    try {
      let corpus = [];

      if (selectedFile) {
        const fileBase64 = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result.split(',')[1] || reader.result);
          reader.onerror = reject;
          reader.readAsDataURL(selectedFile);
        });

        const uploadRes = await fetch(`${API_BASE}/upload_resume`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ file_name: selectedFile.name, content: fileBase64 })
        });
        const uploadData = await uploadRes.json();
        if (uploadData.path) {
          corpus.push({ id: selectedFile.name.replace('.pdf', ''), pdf_path: uploadData.path });
        }
      }

      const response = await fetch(`${API_BASE}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal, standard, corpus })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setRunResult(data);

      if (data.final_state) {
        setCompletedNodes(data.final_state.completed || ['sourcing', 'screening', 'scheduling']);
        if (data.final_state.top_candidate) {
          setInterviewId(`iv-${data.final_state.top_candidate}`);
        }
      }
    } catch (err) {
      console.error('Pipeline execution error:', err);
      setErrorMessage(`Pipeline Error: ${err.message}. Ensure backend is running on ${API_BASE}.`);
    } finally {
      setActiveNode('');
      setRunning(false);
    }
  };

  const handleDeployManagerDebrief = async () => {
    if (!runResult?.run_id) return;
    try {
      setDebriefDeployed(true);
      await fetch(`${API_BASE}/manager_debrief/deploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: runResult.run_id })
      });
    } catch (err) {
      console.error('Failed deploying manager debrief:', err);
    }
  };

  const managerDebriefInfo = runResult?.final_state?.report?.manager_debrief;
  const candidateRoomUrl = runResult?.final_state?.results?.scheduling?.room_url || runResult?.room_url || runResult?.results?.scheduling?.room_url;

  return (
    <div className="min-h-screen bg-[var(--color-canvas)] text-[var(--color-text-primary)] p-8">
      <header className="mb-8 flex items-center justify-between border-b border-[var(--color-glass-border)] pb-6">
        <div>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-purple-500">
            TalentOps Autonomous Hiring Ecosystem
          </h1>
          <p className="text-[var(--color-text-secondary)] font-mono text-sm mt-2">
            Real-Time Multi-Agent Hiring: Candidate Resume PDF → In-Platform Room → Live Interview → Manager AI Debrief
          </p>
        </div>
        
        {/* Controls */}
        <div className="flex gap-4 items-center">
          <input 
            type="text" 
            value={interviewId} 
            onChange={(e) => setInterviewId(e.target.value)} 
            className="bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] rounded-md px-4 py-2 font-mono text-sm focus:outline-none focus:border-cyan-500"
            placeholder="Interview ID"
          />
          <DeployBot 
            roleId={roleId} 
            candidateId={candidateId}
            interviewId={interviewId}
            onDeployed={(id) => setInterviewId(id)}
            onEnded={() => setActiveTab('hr')} 
          />
        </div>
      </header>

      {!supabase && (
        <div className="glass-panel p-4 mb-6 text-amber-500 flex items-center gap-3">
          <span className="text-xl">⚠️</span>
          <p className="text-sm">Running in standalone mode. Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY for live DB streaming.</p>
        </div>
      )}

      {errorMessage && (
        <div className="glass-panel p-4 mb-6 text-red-400 bg-red-950/40 border-red-500/50 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xl">❌</span>
            <p className="text-sm font-mono">{errorMessage}</p>
          </div>
          <button onClick={() => setErrorMessage('')} className="text-xs text-gray-400 hover:text-white">Dismiss</button>
        </div>
      )}

      {/* Top Section: Hiring Goal Input & LangGraph Pipeline Visualizer */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-1 glass-panel p-6 flex flex-col justify-between">
          <div>
            <h2 className="text-lg font-bold mb-3 text-cyan-400">🎯 Hiring Goal & Candidate Resume</h2>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-[var(--color-text-secondary)] uppercase tracking-wider block mb-1">Hiring Role Goal</label>
                <input
                  type="text"
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  className="w-full bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] rounded-md p-2 text-sm focus:outline-none focus:border-cyan-500"
                />
              </div>
              <div>
                <label className="text-xs text-[var(--color-text-secondary)] uppercase tracking-wider block mb-1">Evaluation Standard</label>
                <textarea
                  value={standard}
                  onChange={(e) => setStandard(e.target.value)}
                  rows="2"
                  className="w-full bg-[var(--color-glass-base)] border border-[var(--color-glass-border)] rounded-md p-2 text-sm focus:outline-none focus:border-cyan-500"
                />
              </div>
              <UploadZone onFileSelect={(file) => setSelectedFile(file)} />
            </div>
          </div>
          <button
            onClick={handleRunPipeline}
            disabled={running}
            className="w-full py-3 px-4 mt-4 bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-400 hover:to-purple-500 font-bold rounded-lg transition-all shadow-lg shadow-cyan-500/20 disabled:opacity-50"
          >
            {running ? '⚡ Autonomous Agents Working...' : '🚀 Start Real Hiring Pipeline'}
          </button>
        </div>

        <div className="lg:col-span-2 space-y-4">
          <PipelineVisualizer activeNode={activeNode} completedNodes={completedNodes} />
          {runResult && (
            <div className="glass-panel p-5 space-y-3 bg-cyan-950/20 border-cyan-500/30">
              <div className="flex justify-between items-center text-xs font-mono border-b border-cyan-500/20 pb-2">
                <div><span className="text-cyan-400 font-bold">Run ID:</span> {runResult.run_id}</div>
                <div><span className="text-purple-400 font-bold">Decision:</span> <span className="text-amber-400 font-bold px-2 py-0.5 rounded bg-amber-500/20">{runResult.final_state?.stage || 'WAITING_FOR_INTERVIEW'}</span></div>
                <div><span className="text-cyan-400 font-bold">Top Candidate:</span> {runResult.final_state?.top_candidate || 'Candidate'}</div>
              </div>

              {/* Candidate In-Platform Interview Room Card */}
              {candidateRoomUrl && (
                <div className="p-4 rounded-lg bg-gradient-to-r from-emerald-900/40 to-teal-900/40 border border-emerald-500/40 flex flex-col md:flex-row justify-between items-center gap-4">
                  <div>
                    <h3 className="text-sm font-bold text-emerald-300 flex items-center gap-2">
                      <span>📹</span> Candidate In-Platform Interview Room
                    </h3>
                    <p className="text-xs text-gray-300 mt-1">
                      WebRTC & WebSocket self-hosted interview room created for {runResult.final_state?.top_candidate || 'Candidate'}.
                    </p>
                    <div className="text-xs font-mono text-emerald-400 mt-1">
                      Room Link: <a href={candidateRoomUrl} target="_blank" rel="noreferrer" className="underline">{candidateRoomUrl}</a>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <a
                      href={candidateRoomUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-black font-bold text-xs rounded-md shadow transition-all flex items-center gap-1"
                    >
                      <span>🚀</span> Join Candidate Interview Room
                    </a>
                  </div>
                </div>
              )}

              {/* Manager AI Debrief Meet Session Card */}
              {managerDebriefInfo && (
                <div className="p-4 rounded-lg bg-gradient-to-r from-cyan-900/40 to-purple-900/40 border border-cyan-500/40 flex flex-col md:flex-row justify-between items-center gap-4">
                  <div>
                    <h3 className="text-sm font-bold text-cyan-300 flex items-center gap-2">
                      <span>🧠</span> Manager AI Voice Debrief Session
                    </h3>
                    <p className="text-xs text-gray-300 mt-1">
                      Receive a real-time voice briefing from the AI Manager Agent.
                    </p>
                    <div className="text-xs font-mono text-cyan-400 mt-1">
                      Room Link: <a href={managerDebriefInfo.meet_link} target="_blank" rel="noreferrer" className="underline">{managerDebriefInfo.meet_link}</a>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <a
                      href={managerDebriefInfo.meet_link}
                      target="_blank"
                      rel="noreferrer"
                      onClick={handleDeployManagerDebrief}
                      className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-black font-bold text-xs rounded-md shadow transition-all flex items-center gap-1"
                    >
                      <span>🎙️</span> Join Manager Room
                    </a>
                    {debriefDeployed && (
                      <span className="px-2 py-2 bg-green-500/20 text-green-400 text-xs font-mono rounded flex items-center">
                        ✓ AI Agent Active in Call
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* View Mode Navigation Tabs */}
      <div className="flex gap-2 mb-6 border-b border-[var(--color-glass-border)] pb-3">
        <button
          onClick={() => setActiveTab('live')}
          className={`px-4 py-2 rounded-lg font-bold text-xs transition-all flex items-center gap-2 ${
            activeTab === 'live'
              ? 'bg-cyan-500 text-black shadow-lg shadow-cyan-500/20'
              : 'bg-[var(--color-glass-base)] text-gray-400 hover:text-white border border-[var(--color-glass-border)]'
          }`}
        >
          <span>🎙️</span> Live Audio Stream & Pipeline
        </button>
        <button
          onClick={() => setActiveTab('hr')}
          className={`px-4 py-2 rounded-lg font-bold text-xs transition-all flex items-center gap-2 ${
            activeTab === 'hr'
              ? 'bg-purple-500 text-white shadow-lg shadow-purple-500/20'
              : 'bg-[var(--color-glass-base)] text-gray-400 hover:text-white border border-[var(--color-glass-border)]'
          }`}
        >
          <span>📊</span> HR Evaluation Report Dashboard
        </button>
      </div>

      {/* Conditional View Mode Content */}
      {activeTab === 'hr' ? (
        <HREvaluationDashboard interviewId={interviewId} />
      ) : (
        /* Main Grid: Live Audio Stream, Scorecard & Fairness Lens */
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="flex flex-col gap-8 h-[650px]">
            <div className="flex-1 min-h-0 relative">
               <TranscriptStream supabase={supabase} interviewId={interviewId} />
            </div>
          </div>

          <div className="flex flex-col gap-8 h-[650px]">
            <div className="flex-1 min-h-0">
               <FairnessHeatmap roleId={roleId} />
            </div>
            <div className="flex-1 min-h-0">
               <ScorecardView supabase={supabase} interviewId={interviewId} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
