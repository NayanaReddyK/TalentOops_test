"""Manager Agent live reporting meeting (Task 6.1) — user voice context, read-only."""
from app.services.database import db
from app.services.session_broker import broker, VoiceSession
from app.services.vexa_client import VexaClient

FORBIDDEN = ("change the rubric", "modify", "alter", "re-run", "rerun", "dispatch")
REFUSAL = ("This is a read-only reporting meeting: I can't run sub-agents or alter "
           "rubric/pipeline data mid-meeting. I can answer from the latest pipeline state.")


class ManagerVoiceMeeting:
    def __init__(self, role_id: str, session_factory=None) -> None:
        self.role_id = role_id
        self._session_factory = session_factory
        self.session: VoiceSession | None = None
        self.live = None
        self._vexa = VexaClient()
        self._meeting: dict | None = None
        self._barged = False

    async def start(self, meet_url: str) -> dict:
        # voice ownership: manager may ONLY obtain a user-context session
        self.session = broker.issue_session("manager", "user")
        self._meeting = await self._vexa.join_meeting(meet_url, "TalentOps Manager", "user")
        if self._session_factory:
            self.live = self._session_factory(self.session)
        return {"meeting_id": self._meeting["meeting_id"],
                "session_id": self.session.session_id}

    async def answer(self, question: str) -> str:
        low = question.lower()
        if any(f in low for f in FORBIDDEN):
            return REFUSAL
        try:
            candidates = await db.query("candidates", role_id=self.role_id)
        except Exception:
            candidates = []
        try:
            scorecards = await db.query("scorecards")
        except Exception:
            scorecards = []
        try:
            interviews = await db.query("interviews", role_id=self.role_id)
        except Exception:
            interviews = []
            
        names = ", ".join(c.get("name", "?") for c in candidates) or "none yet"
        return (f"Pipeline state: {len(candidates)} candidate(s) ({names}); "
                f"{len(interviews)} interview(s) recorded; {len(scorecards)} scorecard(s) complete.")

    def barge_in(self) -> None:
        self._barged = True  # turn-taking handled natively by Gemini Live VAD

    async def close(self) -> None:
        if self.session:
            broker.close_session(self.session.session_id)
        if self._meeting:
            await self._vexa.leave_meeting(self._meeting["meeting_id"])
