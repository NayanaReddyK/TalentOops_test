import React, { useState } from 'react';
import { createClient } from '@supabase/supabase-js';
import { Rocket, BarChart3, ClipboardList, Upload, ChevronRight, AlertCircle, X, Loader2 } from 'lucide-react';

import UploadZone from './components/UploadZone';
import PipelineVisualizer from './components/PipelineVisualizer';
import TranscriptStream from './components/TranscriptStream';
import FairnessHeatmap from './components/FairnessHeatmap';
import ScorecardView from './components/ScorecardView';
import HREvaluationDashboard from './components/HREvaluationDashboard';
import InterviewRoom from './components/InterviewRoom';

// ── Supabase & API ────────────────────────────────────────────────────
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://qzthddhmxdcocikdhumh.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF6dGhkZGhteGRjb2Npa2RodW1oIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQxNjc4MjAsImV4cCI6MjA5OTc0MzgyMH0.VJbR0Ad8t9SgsAPc9XyFM3bkLrPocmEekjOnnPwoJss';
const supabase = supabaseUrl && supabaseAnonKey ? createClient(supabaseUrl, supabaseAnonKey) : null;
const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

// ── Navigation Items ──────────────────────────────────────────────────
const NAV_ITEMS = [
  { id: 'pipeline', label: 'Pipeline', icon: Rocket, description: 'Upload & Run' },
  { id: 'results',  label: 'Results',  icon: BarChart3, description: 'Scorecard & Transcript' },
  { id: 'evaluation', label: 'Evaluation', icon: ClipboardList, description: 'HR Report & Debrief' },
];

function App() {
  // ── Interview Room route ────────────────────────────────────────────
  const pathMatch = window.location.pathname.match(/^\/interview\/([\w-]+)/);
  if (pathMatch) {
    return <InterviewRoom roomId={pathMatch[1]} />;
  }

  // ── State ───────────────────────────────────────────────────────────
  const urlParams = new URLSearchParams(window.location.search);
  const [roleId] = useState(urlParams.get('roleId') || 'r1');
  const [activeView, setActiveView] = useState('pipeline');
  const [interviewId, setInterviewId] = useState(urlParams.get('interviewId') || '');

  // Pipeline state
  const [goal, setGoal] = useState('Hire a Senior Backend Engineer (Python, FastAPI, Postgres)');
  const [standard, setStandard] = useState('Strong experience with async Python, distributed systems, and SQL optimization');
  const [selectedFile, setSelectedFile] = useState(null);
  const [running, setRunning] = useState(false);
  const [activeNode, setActiveNode] = useState('');
  const [completedNodes, setCompletedNodes] = useState([]);
  const [runResult, setRunResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  // ── Pipeline Execution ──────────────────────────────────────────────
  const handleRunPipeline = async () => {
    setRunning(true);
    setActiveNode('sourcing');
    setCompletedNodes([]);
    setRunResult(null);
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

      if (!response.ok) throw new Error(`Server returned ${response.status}`);

      const data = await response.json();
      setRunResult(data);

      if (data.final_state) {
        setCompletedNodes(data.final_state.completed || ['sourcing', 'screening', 'scheduling']);
        if (data.final_state.top_candidate) {
          setInterviewId(`iv-${data.final_state.top_candidate}`);
        }
      }

      // Auto-switch to results view after pipeline completes
      setActiveView('results');
    } catch (err) {
      console.error('Pipeline execution error:', err);
      setErrorMessage(err.message || 'Failed to connect to backend.');
    } finally {
      setActiveNode('');
      setRunning(false);
    }
  };

  const candidateRoomUrl =
    runResult?.final_state?.results?.scheduling?.room_url ||
    runResult?.room_url ||
    runResult?.results?.scheduling?.room_url;

  // ── Render ──────────────────────────────────────────────────────────
  return (
    <div className="flex h-screen overflow-hidden bg-[var(--color-canvas)]">
      {/* ── Sidebar ────────────────────────────────────────────────── */}
      <nav className="w-[220px] shrink-0 border-r border-[var(--color-glass-border)] flex flex-col bg-[var(--color-surface)]">
        {/* Logo */}
        <div className="p-5 border-b border-[var(--color-glass-border)]">
          <h1 className="text-lg font-bold text-[var(--color-text-primary)] tracking-tight">
            TalentOps
          </h1>
          <p className="text-[11px] text-[var(--color-text-muted)] mt-0.5 font-medium">
            AI Hiring Platform
          </p>
        </div>

        {/* Nav Items */}
        <div className="flex-1 p-3 flex flex-col gap-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;
            const isDisabled = (item.id === 'results' || item.id === 'evaluation') && !runResult && !interviewId;

            return (
              <button
                key={item.id}
                onClick={() => !isDisabled && setActiveView(item.id)}
                disabled={isDisabled}
                className={`w-full text-left px-3 py-2.5 rounded-xl flex items-center gap-3 transition-all duration-200 group ${
                  isActive
                    ? 'bg-[var(--color-accent-muted)] text-[var(--color-accent)]'
                    : isDisabled
                    ? 'text-[var(--color-text-muted)] cursor-not-allowed opacity-40'
                    : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-glass-hover)] hover:text-[var(--color-text-primary)]'
                }`}
              >
                <Icon size={18} strokeWidth={isActive ? 2.5 : 2} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold leading-tight">{item.label}</div>
                  <div className="text-[10px] opacity-60 leading-tight mt-0.5">{item.description}</div>
                </div>
                {isActive && (
                  <ChevronRight size={14} className="opacity-50" />
                )}
              </button>
            );
          })}
        </div>

        {/* Pipeline Status Badge */}
        {runResult && (
          <div className="p-3 border-t border-[var(--color-glass-border)]">
            <div className="px-3 py-2 rounded-lg bg-[var(--color-emerald-muted)] text-emerald-400 text-xs font-medium flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-400" />
              Pipeline Complete
            </div>
          </div>
        )}
        {running && (
          <div className="p-3 border-t border-[var(--color-glass-border)]">
            <div className="px-3 py-2 rounded-lg bg-[var(--color-accent-muted)] text-[var(--color-accent)] text-xs font-medium flex items-center gap-2">
              <Loader2 size={12} className="animate-spin" />
              Running Pipeline...
            </div>
          </div>
        )}
      </nav>

      {/* ── Main Content ───────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto">
        {/* Error Banner */}
        {errorMessage && (
          <div className="m-6 mb-0 p-4 rounded-xl bg-[var(--color-rose-muted)] border border-rose-500/20 text-rose-300 flex items-center justify-between gap-4 animate-fade-in">
            <div className="flex items-center gap-3">
              <AlertCircle size={18} />
              <span className="text-sm">{errorMessage}</span>
            </div>
            <button onClick={() => setErrorMessage('')} className="text-rose-400 hover:text-rose-300 p-1">
              <X size={16} />
            </button>
          </div>
        )}

        <div className="p-6 lg:p-8">
          {/* ── Pipeline View ──────────────────────────────────────── */}
          {activeView === 'pipeline' && (
            <div className="animate-fade-in max-w-5xl mx-auto">
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">Hiring Pipeline</h2>
                <p className="text-sm text-[var(--color-text-secondary)] mt-1">
                  Upload a candidate resume, define the role, and let the AI agents handle the rest.
                </p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
                {/* Left: Configuration */}
                <div className="lg:col-span-3 space-y-5">
                  {/* Role Goal */}
                  <div className="card">
                    <div className="card-body space-y-4">
                      <div>
                        <label className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-2 block">
                          Hiring Role
                        </label>
                        <input
                          type="text"
                          value={goal}
                          onChange={(e) => setGoal(e.target.value)}
                          className="input"
                          placeholder="e.g. Senior Backend Engineer"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-2 block">
                          Evaluation Criteria
                        </label>
                        <textarea
                          value={standard}
                          onChange={(e) => setStandard(e.target.value)}
                          rows="2"
                          className="input textarea"
                          placeholder="What skills and experience should we evaluate?"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Upload Zone */}
                  <UploadZone onFileSelect={(file) => setSelectedFile(file)} />

                  {/* Run Button */}
                  <button
                    onClick={handleRunPipeline}
                    disabled={running}
                    className="btn btn-primary w-full py-3.5 text-base"
                  >
                    {running ? (
                      <>
                        <Loader2 size={18} className="animate-spin" />
                        Agents Processing...
                      </>
                    ) : (
                      <>
                        <Rocket size={18} />
                        Start Hiring Pipeline
                      </>
                    )}
                  </button>

                  {/* Room URL Card */}
                  {candidateRoomUrl && (
                    <div className="card animate-fade-in">
                      <div className="card-body flex items-center justify-between gap-4">
                        <div>
                          <p className="text-sm font-semibold text-emerald-400">Interview Room Ready</p>
                          <p className="text-xs text-[var(--color-text-muted)] mt-1 font-mono truncate max-w-sm">{candidateRoomUrl}</p>
                        </div>
                        <a
                          href={candidateRoomUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn-secondary btn-sm shrink-0"
                        >
                          Open Room
                        </a>
                      </div>
                    </div>
                  )}
                </div>

                {/* Right: Pipeline Progress */}
                <div className="lg:col-span-2">
                  <PipelineVisualizer activeNode={activeNode} completedNodes={completedNodes} />

                  {/* Run Summary */}
                  {runResult && (
                    <div className="card mt-5 animate-fade-in">
                      <div className="card-body space-y-3">
                        <h4 className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">Run Summary</h4>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-[var(--color-text-muted)]">Run ID</span>
                            <span className="font-mono text-xs text-[var(--color-text-secondary)]">{runResult.run_id}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-[var(--color-text-muted)]">Stage</span>
                            <span className="badge bg-[var(--color-accent-muted)] text-[var(--color-accent)]">
                              {runResult.final_state?.stage || 'COMPLETE'}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-[var(--color-text-muted)]">Top Candidate</span>
                            <span className="font-semibold">{runResult.final_state?.top_candidate || '—'}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ── Results View ───────────────────────────────────────── */}
          {activeView === 'results' && (
            <div className="animate-fade-in">
              <div className="mb-8 flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">Results</h2>
                  <p className="text-sm text-[var(--color-text-secondary)] mt-1">
                    Interview transcript, candidate scorecard, and fairness analysis.
                  </p>
                </div>
                {interviewId && (
                  <span className="badge bg-[var(--color-glass-hover)] text-[var(--color-text-secondary)] border border-[var(--color-glass-border)]">
                    {interviewId}
                  </span>
                )}
              </div>

              {!runResult && !interviewId ? (
                <div className="card">
                  <div className="card-body py-20 text-center">
                    <BarChart3 size={40} className="mx-auto text-[var(--color-text-muted)] mb-4" />
                    <p className="text-[var(--color-text-secondary)] font-medium">No results yet</p>
                    <p className="text-sm text-[var(--color-text-muted)] mt-1">Run the hiring pipeline first to see results here.</p>
                    <button onClick={() => setActiveView('pipeline')} className="btn btn-secondary btn-sm mt-4">
                      Go to Pipeline
                    </button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                  <div className="xl:row-span-2 min-h-[500px]">
                    <TranscriptStream supabase={supabase} interviewId={interviewId || 'iv-alex'} />
                  </div>
                  <div className="min-h-[280px]">
                    <ScorecardView supabase={supabase} interviewId={interviewId || 'iv-alex'} />
                  </div>
                  <div className="min-h-[280px]">
                    <FairnessHeatmap roleId={roleId} />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── Evaluation View ─────────────────────────────────────── */}
          {activeView === 'evaluation' && (
            <div className="animate-fade-in">
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-[var(--color-text-primary)]">Evaluation Report</h2>
                <p className="text-sm text-[var(--color-text-secondary)] mt-1">
                  Comprehensive AI evaluation, competency analysis, and manager debrief.
                </p>
              </div>

              {!runResult && !interviewId ? (
                <div className="card">
                  <div className="card-body py-20 text-center">
                    <ClipboardList size={40} className="mx-auto text-[var(--color-text-muted)] mb-4" />
                    <p className="text-[var(--color-text-secondary)] font-medium">No evaluation available</p>
                    <p className="text-sm text-[var(--color-text-muted)] mt-1">Run the hiring pipeline first to generate an evaluation.</p>
                    <button onClick={() => setActiveView('pipeline')} className="btn btn-secondary btn-sm mt-4">
                      Go to Pipeline
                    </button>
                  </div>
                </div>
              ) : (
                <HREvaluationDashboard interviewId={interviewId || 'iv-alex'} />
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
