"""Consent announcement + call gating (Task 4.6): no interaction before acknowledgment."""
from datetime import datetime, timezone

from app.services.session_broker import VoiceSession

CONSENT_SCRIPT = (
    "This call is recorded and transcribed by TalentOps for interview evaluation "
    "and audit purposes. By continuing, you consent to this recording. "
    "Say 'I agree' to continue, or leave the call now."
)


class ConsentError(Exception):
    """Interaction attempted before recording consent was acknowledged."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class VoiceChain:
    def __init__(self, session: VoiceSession) -> None:
        self.session = session
        self._consent = False
        self._started: str | None = None
        self._ended: str | None = None

    async def open_call(self) -> dict:
        self._started = _now()
        return {"announcement": CONSENT_SCRIPT, "session_id": self.session.session_id}

    def acknowledge_consent(self) -> None:
        self._consent = True

    async def interact(self, text: str) -> str:
        if not self._consent:
            raise ConsentError("call invalid: consent_acknowledged is false")
        ctx = getattr(self.session, "voice_context", None)
        if not ctx or not isinstance(ctx, str):
            ctx = getattr(self.session, "session_id", "session")
        return f"[{ctx}] {text}"

    async def end_call(self) -> None:
        self._ended = _now()

    def call_meta(self) -> dict:
        return {
            "consent_acknowledged": self._consent,
            "started_ts": self._started or "",
            "ended_ts": self._ended or _now(),
        }
