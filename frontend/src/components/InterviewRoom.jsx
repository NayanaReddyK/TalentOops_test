import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Mic, MicOff, Video, VideoOff, PhoneOff, CheckCircle, XCircle, Loader2, Activity, Award, MessageSquare } from 'lucide-react';

/* ─── helpers ─────────────────────────────────────────────────────────────── */
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
const WS_BASE  = API_BASE.replace(/^http/, 'ws');

function ScoreBar({ label, value }) {
  const pct = Math.round((value || 0) * 100);
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-300">{label}</span>
        <span className="text-cyan-400 font-mono">{pct}%</span>
      </div>
      <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full transition-all duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function TranscriptBubble({ turn }) {
  const isAgent = turn.speaker === 'interviewer' || turn.speaker === 'agent';
  return (
    <div className={`flex gap-3 mb-3 ${isAgent ? '' : 'flex-row-reverse'}`}>
      <div className={`w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold
        ${isAgent ? 'bg-cyan-500/30 text-cyan-300' : 'bg-violet-500/30 text-violet-300'}`}>
        {isAgent ? 'AI' : 'C'}
      </div>
      <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed
        ${isAgent
          ? 'bg-white/10 text-slate-200 rounded-tl-none'
          : 'bg-cyan-600/30 text-cyan-100 rounded-tr-none'}`}>
        {turn.text}
      </div>
    </div>
  );
}

/* ─── stages ──────────────────────────────────────────────────────────────── */
const STAGE = {
  LOBBY:      'lobby',
  CONSENT:    'consent',
  INTERVIEW:  'interview',
  EVALUATING: 'evaluating',
  COMPLETE:   'complete',
  ERROR:      'error',
};

/* ─── main component ─────────────────────────────────────────────────────── */
export default function InterviewRoom({ roomId }) {
  const [stage,       setStage]       = useState(STAGE.LOBBY);
  const [micOn,       setMicOn]       = useState(true);
  const [camOn,       setCamOn]       = useState(true);
  const [consentText, setConsentText] = useState('');
  const [disclosure,  setDisclosure]  = useState('');
  const [transcript,  setTranscript]  = useState([]);
  const [turnInput,   setTurnInput]   = useState('');
  const [scorecard,   setScorecard]   = useState(null);
  const [behavMetrics, setBehavMetrics] = useState(null);
  const [recommendation, setRecommendation] = useState(null);
  const [errorMsg,    setErrorMsg]    = useState('');
  const [roomMeta,    setRoomMeta]    = useState(null);

  const wsRef          = useRef(null);
  const localVideoRef  = useRef(null);
  const localStream    = useRef(null);
  const transcriptEnd  = useRef(null);

  /* ── webcam preview ─────────────────────────────────────────────────────── */
  useEffect(() => {
    let stream;
    navigator.mediaDevices?.getUserMedia({ video: true, audio: true })
      .then(s => {
        stream = s;
        localStream.current = s;
        if (localVideoRef.current) localVideoRef.current.srcObject = s;
      })
      .catch(() => {/* mic/cam denied — non-fatal */});
    return () => {
      stream?.getTracks().forEach(t => t.stop());
    };
  }, []);

  useEffect(() => {
    if (localStream.current) {
      localStream.current.getAudioTracks().forEach(t => (t.enabled = micOn));
    }
  }, [micOn]);

  useEffect(() => {
    if (localStream.current) {
      localStream.current.getVideoTracks().forEach(t => (t.enabled = camOn));
    }
  }, [camOn]);

  /* ── auto-scroll transcript ─────────────────────────────────────────────── */
  useEffect(() => {
    transcriptEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript]);

  /* ── WebSocket connection ───────────────────────────────────────────────── */
  const connectWs = useCallback(() => {
    if (!roomId) return;
    const ws = new WebSocket(`${WS_BASE}/ws/room/${roomId}`);
    wsRef.current = ws;

    ws.onopen = () => setStage(STAGE.CONSENT);

    ws.onmessage = (event) => {
      let msg;
      try { msg = JSON.parse(event.data); } catch { return; }
      const { type, data } = msg;

      switch (type) {
        case 'room-joined':
          setRoomMeta(data);
          break;

        case 'consent-ask':
          setDisclosure(data.text || '');
          break;

        case 'agent-message':
          if (data.agent === 'consent' && data.consent_granted) {
            setStage(STAGE.INTERVIEW);
          } else if (data.agent === 'consent' && !data.consent_granted) {
            setStage(STAGE.ERROR);
            setErrorMsg('Consent was not granted. Session ended.');
          }
          break;

        case 'interview-turn':
          setTranscript(prev => [...prev, { speaker: data.speaker, text: data.text }]);
          break;

        case 'eval-update':
          setScorecard(data.scorecard || null);
          setBehavMetrics(data.behavioral_metrics || null);
          setRecommendation(data.final_recommendation || null);
          setStage(STAGE.EVALUATING);
          break;

        case 'session-end':
          setStage(STAGE.COMPLETE);
          if (data.scorecard) setScorecard(data.scorecard);
          break;

        case 'error':
          setStage(STAGE.ERROR);
          setErrorMsg(data.message || 'An unknown error occurred.');
          break;

        default:
          break;
      }
    };

    ws.onerror = () => {
      setStage(STAGE.ERROR);
      setErrorMsg('WebSocket connection lost. Please refresh and try again.');
    };

    ws.onclose = () => { wsRef.current = null; };
  }, [roomId]);

  const sendFrame = (type, data = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, data }));
    }
  };

  const handleJoin = () => connectWs();

  const handleConsent = () => {
    if (!consentText.trim()) return;
    setTranscript([{ speaker: 'agent', text: disclosure }]);
    sendFrame('consent-response', { text: consentText });
  };

  const handleTurnSend = () => {
    if (!turnInput.trim()) return;
    setTranscript(prev => [...prev, { speaker: 'candidate', text: turnInput }]);
    sendFrame('interview-turn', { text: turnInput });
    setTurnInput('');
  };

  const handleEnd = async () => {
    sendFrame('session-end');
    wsRef.current?.close();
    await fetch(`${API_BASE}/rooms/${roomId}/end`, { method: 'POST' }).catch(() => {});
    setStage(STAGE.COMPLETE);
  };

  /* ─── render ─────────────────────────────────────────────────────────────── */
  return (
    <div className="min-h-screen bg-[#070b14] text-white font-sans flex flex-col"
         style={{ fontFamily: "'Inter', sans-serif" }}>

      {/* ── top bar ────────────────────────────────────────────────────────── */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-white/10
                         bg-white/5 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <span className="text-cyan-400 font-bold text-lg tracking-tight">TalentOops</span>
          <span className="text-slate-500">|</span>
          <span className="text-slate-400 text-sm">Interview Room</span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className={`w-2 h-2 rounded-full ${
            stage === STAGE.INTERVIEW || stage === STAGE.EVALUATING
              ? 'bg-green-400 animate-pulse' : 'bg-slate-600'
          }`} />
          <span className="text-slate-400 font-mono">{roomId?.slice(0,8) ?? '---'}</span>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">

        {/* ── left: video + controls ─────────────────────────────────────── */}
        <div className="w-72 flex-shrink-0 flex flex-col gap-4 p-4 border-r border-white/10 bg-white/3">
          {/* local video */}
          <div className="relative rounded-xl overflow-hidden bg-slate-800/60 aspect-video">
            <video
              ref={localVideoRef}
              autoPlay
              muted
              playsInline
              className={`w-full h-full object-cover ${!camOn ? 'opacity-0' : ''}`}
            />
            {!camOn && (
              <div className="absolute inset-0 flex items-center justify-center">
                <VideoOff size={28} className="text-slate-500" />
              </div>
            )}
            <div className="absolute bottom-2 left-2 text-xs bg-black/50 px-2 py-0.5 rounded-full text-slate-300">
              You
            </div>
          </div>

          {/* mic / cam toggles */}
          <div className="flex gap-2">
            <button
              onClick={() => setMicOn(v => !v)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm font-medium transition-all
                ${micOn ? 'bg-white/10 hover:bg-white/15 text-slate-200'
                         : 'bg-rose-500/20 border border-rose-500/50 text-rose-400'}`}
            >
              {micOn ? <Mic size={15} /> : <MicOff size={15} />}
              {micOn ? 'Mic On' : 'Muted'}
            </button>
            <button
              onClick={() => setCamOn(v => !v)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-sm font-medium transition-all
                ${camOn ? 'bg-white/10 hover:bg-white/15 text-slate-200'
                         : 'bg-rose-500/20 border border-rose-500/50 text-rose-400'}`}
            >
              {camOn ? <Video size={15} /> : <VideoOff size={15} />}
              {camOn ? 'Camera' : 'Off'}
            </button>
          </div>

          {/* scorecard sidebar */}
          {(behavMetrics || scorecard) && (
            <div className="flex-1 overflow-y-auto rounded-xl bg-white/5 p-4 border border-white/10">
              <div className="flex items-center gap-2 mb-4">
                <Activity size={14} className="text-cyan-400" />
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Live Scores</span>
              </div>
              {behavMetrics && <>
                <ScoreBar label="Confidence"    value={behavMetrics.confidence_level} />
                <ScoreBar label="Clarity"       value={behavMetrics.communication_clarity} />
                <ScoreBar label="Engagement"    value={behavMetrics.candidate_engagement} />
              </>}
              {recommendation && (
                <div className="mt-4 p-3 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
                  <div className="text-xs text-slate-400 mb-1">Recommendation</div>
                  <div className="text-sm font-bold text-cyan-300">
                    {recommendation.hiring_recommendation}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    Score: {recommendation.overall_suitability_score}%
                  </div>
                </div>
              )}
            </div>
          )}

          {/* end session button */}
          {(stage === STAGE.INTERVIEW || stage === STAGE.EVALUATING) && (
            <button
              onClick={handleEnd}
              className="flex items-center justify-center gap-2 py-2.5 rounded-lg
                         bg-rose-500/10 border border-rose-500/30 text-rose-400
                         hover:bg-rose-500/20 transition-all text-sm font-medium"
            >
              <PhoneOff size={15} /> End Session
            </button>
          )}
        </div>

        {/* ── centre: stage content ──────────────────────────────────────── */}
        <div className="flex-1 flex flex-col items-center justify-center p-8 overflow-y-auto">

          {/* LOBBY */}
          {stage === STAGE.LOBBY && (
            <div className="w-full max-w-md">
              <div className="text-center mb-8">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center mx-auto mb-4 shadow-[0_0_40px_rgba(6,182,212,0.35)]">
                  <MessageSquare size={28} className="text-white" />
                </div>
                <h1 className="text-2xl font-bold text-white mb-2">Ready to Join?</h1>
                <p className="text-slate-400 text-sm leading-relaxed">
                  Your interview room is prepared. Make sure your microphone and camera are working.
                </p>
              </div>
              <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-6 space-y-3">
                <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Before you begin</p>
                {['Microphone and camera are permitted in your browser',
                  'You are in a quiet environment',
                  'Stable internet connection',
                  'This session will be recorded with your consent'].map(item => (
                  <div key={item} className="flex items-start gap-2 text-sm text-slate-300">
                    <CheckCircle size={15} className="text-cyan-400 flex-shrink-0 mt-0.5" />
                    {item}
                  </div>
                ))}
              </div>
              <button
                id="btn-join-room"
                onClick={handleJoin}
                className="w-full py-3.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600
                           hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-base
                           shadow-[0_0_25px_rgba(6,182,212,0.4)] transition-all"
              >
                Join Interview Room
              </button>
            </div>
          )}

          {/* CONSENT */}
          {stage === STAGE.CONSENT && (
            <div className="w-full max-w-lg">
              <h2 className="text-xl font-bold text-white mb-2 text-center">Recording Consent</h2>
              <p className="text-slate-400 text-sm text-center mb-6">Please read and respond to the following disclosure.</p>
              <div className="bg-amber-500/10 border border-amber-500/25 rounded-2xl p-5 mb-6 text-sm text-amber-200 leading-relaxed">
                {disclosure || 'This session will be recorded and evaluated by our AI system for objective scoring. Do you consent?'}
              </div>
              <input
                id="input-consent"
                type="text"
                value={consentText}
                onChange={e => setConsentText(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleConsent()}
                placeholder='Type "yes I consent" to proceed…'
                className="w-full bg-white/8 border border-white/15 rounded-xl px-4 py-3
                           text-white placeholder:text-slate-500 text-sm mb-4
                           focus:outline-none focus:border-cyan-500 transition-all"
              />
              <div className="flex gap-3">
                <button
                  id="btn-consent-agree"
                  onClick={handleConsent}
                  disabled={!consentText.trim()}
                  className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl
                             bg-gradient-to-r from-cyan-600 to-blue-600 text-white font-semibold
                             disabled:opacity-40 disabled:cursor-not-allowed shadow-[0_0_20px_rgba(6,182,212,0.3)]
                             hover:from-cyan-500 hover:to-blue-500 transition-all"
                >
                  <CheckCircle size={16} /> I Consent &amp; Join
                </button>
                <button
                  id="btn-consent-decline"
                  onClick={() => { sendFrame('session-end'); setStage(STAGE.ERROR); setErrorMsg('Session cancelled.'); }}
                  className="px-5 py-3 rounded-xl border border-white/15 text-slate-400
                             hover:bg-white/5 text-sm transition-all"
                >
                  Decline
                </button>
              </div>
            </div>
          )}

          {/* INTERVIEW */}
          {(stage === STAGE.INTERVIEW || stage === STAGE.EVALUATING) && (
            <div className="w-full max-w-2xl flex flex-col h-full" style={{ maxHeight: '70vh' }}>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-2.5 h-2.5 rounded-full bg-green-400 animate-pulse" />
                <span className="text-sm text-slate-400">Interview in progress</span>
                {stage === STAGE.EVALUATING && (
                  <span className="ml-auto text-xs text-cyan-400 flex items-center gap-1">
                    <Loader2 size={12} className="animate-spin" /> Evaluating…
                  </span>
                )}
              </div>

              {/* transcript scroll area */}
              <div className="flex-1 overflow-y-auto mb-4 pr-1">
                {transcript.map((turn, i) => (
                  <TranscriptBubble key={i} turn={turn} />
                ))}
                <div ref={transcriptEnd} />
              </div>

              {/* answer input */}
              <div className="flex gap-3">
                <input
                  id="input-answer"
                  type="text"
                  value={turnInput}
                  onChange={e => setTurnInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleTurnSend()}
                  placeholder="Type your answer…"
                  className="flex-1 bg-white/8 border border-white/15 rounded-xl px-4 py-3
                             text-white placeholder:text-slate-500 text-sm
                             focus:outline-none focus:border-cyan-500 transition-all"
                />
                <button
                  id="btn-send-turn"
                  onClick={handleTurnSend}
                  disabled={!turnInput.trim()}
                  className="px-5 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500
                             text-white font-medium text-sm transition-all
                             disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Send
                </button>
              </div>
            </div>
          )}

          {/* COMPLETE */}
          {stage === STAGE.COMPLETE && (
            <div className="text-center max-w-md">
              <div className="w-20 h-20 rounded-full bg-green-500/20 border border-green-500/40 flex items-center justify-center mx-auto mb-6">
                <Award size={36} className="text-green-400" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-2">Interview Complete!</h2>
              <p className="text-slate-400 text-sm mb-6 leading-relaxed">
                Your session has been recorded and submitted for evaluation. HR will be in touch.
              </p>
              {recommendation && (
                <div className="bg-white/5 border border-white/10 rounded-2xl p-5 text-left">
                  <div className="text-xs text-slate-400 uppercase tracking-wider mb-3">Session Summary</div>
                  <div className="text-sm text-slate-300 leading-relaxed">
                    {recommendation.executive_summary}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ERROR */}
          {stage === STAGE.ERROR && (
            <div className="text-center max-w-sm">
              <XCircle size={48} className="text-rose-400 mx-auto mb-4" />
              <h2 className="text-xl font-bold text-white mb-2">Session Ended</h2>
              <p className="text-slate-400 text-sm">{errorMsg}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
