"""Streams the Gemini Live auto-transcript into the immutable Supabase audit trail."""
from datetime import datetime, timezone

from app.services.database import db


class TranscriptStreamer:
    def __init__(self, interview_id: str) -> None:
        self.interview_id = interview_id

    async def stream(self, speaker: str, text: str,
                     difficulty_estimate: float | None = None,
                     competency_id: str | None = None) -> None:
        await db.append_transcript(self.interview_id, {
            "speaker": speaker,
            "text": text,
            "difficulty_estimate": difficulty_estimate,
            "competency_id": competency_id,
            "ts": datetime.now(timezone.utc).isoformat(),
        })

    async def finalize(self) -> None:
        await db.finalize_transcript(self.interview_id)
