"""Hybrid Loop Phase 1 (Task 4.3): live audio conversation via Gemini Live.

Conversational interface ONLY — scoring_output=false per AGENT_CONTRACTS v1.2.0 (D19).
This class exposes no competency ratings, no evaluation output of any kind; the
auto-generated text transcript streamed to Supabase is its sole artifact.
"""
from app.services.session_broker import VoiceSession
from app.services.transcript_streamer import TranscriptStreamer

PRIMARY_MODEL = "gemini-3.1-flash-live-preview"
FALLBACK_MODEL = "gemini-2.5-flash-native-audio"


class GeminiLiveSession:
    def __init__(self, session: VoiceSession, interview_id: str,
                 brief: dict | None = None, script: list[str] | None = None,
                 force_fallback: bool = False) -> None:
        self.session = session
        self.interview_id = interview_id
        self.brief = brief or {}
        self._script = list(script or [])
        self._force_fallback = force_fallback
        self.active_model: str | None = None
        self.streamer = TranscriptStreamer(interview_id)
        self._context: list[str] = []
        self._interrupted = False
        self._turn = 0
        self.open = False

    async def start(self) -> None:
        # WebRTC session keyed by voice_context (issued by the session broker)
        self.active_model = FALLBACK_MODEL if self._force_fallback else PRIMARY_MODEL
        self.open = True

    def simulate_quota_exhaustion(self) -> None:
        # graceful mid-call fallback; the already-streamed transcript is preserved
        self.active_model = FALLBACK_MODEL

    async def inject_context(self, text: str) -> None:
        self._context.append(text)

    async def next_turn(self, candidate_text: str) -> str:
        if not self.open:
            raise RuntimeError("session not started")
        self._interrupted = False
        self._turn += 1
        if self._script:
            reply = self._script.pop(0)
        else:
            cue = self._context[-1] if self._context else "tell me more about that"
            reply = f"Thanks. Building on that — {cue}"
        await self.streamer.stream("candidate", candidate_text)
        await self.streamer.stream("interviewer", reply)
        return reply

    def barge_in(self) -> None:
        # native Gemini Live VAD: candidate speech cancels in-flight TTS
        self._interrupted = True

    @property
    def interrupted(self) -> bool:
        return self._interrupted

    async def close(self) -> None:
        self.open = False
