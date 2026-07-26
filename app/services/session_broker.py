"""Session broker — architectural enforcement of the voice ownership rule (arch §2.3)."""
import uuid
from dataclasses import dataclass


class VoiceOwnershipError(Exception):
    """Crossed voice-context request (e.g. interviewer asking for a user session)."""


ALLOWED = {("interviewer", "candidate"), ("manager", "user")}


@dataclass(frozen=True)
class VoiceSession:
    session_id: str
    agent: str
    voice_context: str


class SessionBroker:
    def __init__(self) -> None:
        self.active: dict[str, VoiceSession] = {}

    def issue_session(self, agent: str, voice_context: str) -> VoiceSession:
        if (agent, voice_context) not in ALLOWED:
            raise VoiceOwnershipError(
                f"{agent!r} may not obtain a {voice_context!r}-context session"
            )
        s = VoiceSession(uuid.uuid4().hex, agent, voice_context)
        self.active[s.session_id] = s
        return s

    def close_session(self, session_id: str) -> None:
        self.active.pop(session_id, None)


broker = SessionBroker()
