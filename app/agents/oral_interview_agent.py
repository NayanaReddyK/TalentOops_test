"""Oral Interview Agent Engine: STT/TTS pipeline + Adaptive Q&A + Real-Time Supabase Logging."""
from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from typing import Any

from app.services.conversation_manager import ConversationManager
from app.services.database import db
from app.services.speech_engine import STTService, TTSService
from app.supabase_client import log_event

logger = logging.getLogger("talentops.oral_interview_agent")

_active_managers: dict[str, ConversationManager] = {}


def get_conversation_manager(
    session_id: str, job_description: str = "", parsed_resume: str = ""
) -> ConversationManager:
    if session_id not in _active_managers:
        _active_managers[session_id] = ConversationManager(
            session_id=session_id,
            job_description=job_description,
            parsed_resume=parsed_resume,
        )
    return _active_managers[session_id]


class OralInterviewAgent:
    """Oral speech-based interview agent conducting turn-taking Q&A with real-time Supabase persistence."""

    def __init__(self):
        self.stt = STTService()
        self.tts = TTSService()

    async def process_turn(
        self,
        session_id: str,
        candidate_id: str,
        role_id: str,
        candidate_text: str | None = None,
        candidate_audio_b64: str | None = None,
        run_id: str = "run-oral",
    ) -> dict[str, Any]:
        """Process a single oral interview turn."""
        # 1. Transcribe audio input if provided
        transcript = candidate_text or ""
        if not transcript and candidate_audio_b64:
            try:
                raw_audio = base64.b64decode(candidate_audio_b64)
                transcript = await self.stt.transcribe_audio(raw_audio)
            except Exception as e:
                logger.error("Failed to decode or transcribe audio b64: %s", e)
                transcript = "[Audio transcription unparseable]"

        if not transcript:
            transcript = "Candidate response"

        # 2. Retrieve Candidate Resume & Role Job Description from Supabase DB
        candidates = await db.query("candidates", id=candidate_id)
        candidate_resume = candidates[0].get("resume", "") if candidates else ""

        roles = await db.query("roles", id=role_id)
        job_description = roles[0].get("jd", "") if roles else ""

        # 3. Retrieve ConversationManager instance
        cm = get_conversation_manager(
            session_id=session_id,
            job_description=job_description,
            parsed_resume=candidate_resume,
        )

        # 4. Generate next context-aware question
        question_text = await cm.generate_next_question(candidate_text=transcript)
        question_number = cm.turn_count

        # 5. Synthesize TTS audio response
        audio_b64 = await self.tts.synthesize_speech_b64(question_text)

        # 6. Real-time Supabase Q&A log persistence (interview_qa_logs table)
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        qa_log_payload = {
            "session_id": session_id,
            "question_number": question_number,
            "question_text": question_text,
            "candidate_answer_transcript": transcript,
            "confidence_score": 0.85,
            "metadata": {
                "candidate_id": candidate_id,
                "role_id": role_id,
                "text_length": len(transcript),
            },
            "timestamp": timestamp_iso,
        }

        log_id = f"log-{session_id}-{question_number}"
        try:
            stored_log = await db.insert("interview_qa_logs", qa_log_payload)
            if stored_log and isinstance(stored_log, dict) and stored_log.get("id"):
                log_id = stored_log["id"]
        except Exception as db_err:
            logger.warning("Supabase interview_qa_logs insert warning for session %s: %s; fallback id: %s", session_id, db_err, log_id)

        # 7. Audit log event
        log_event(
            run_id=run_id,
            source="oral_interview_agent",
            event_type="qa_turn_completed",
            payload={
                "session_id": session_id,
                "question_number": question_number,
                "candidate_id": candidate_id,
                "qa_log_id": log_id,
            },
        )

        logger.info(
            "OralInterviewAgent turn %d complete for session %s (candidate: %s)",
            question_number, session_id, candidate_id
        )

        return {
            "session_id": session_id,
            "question_number": question_number,
            "question_text": question_text,
            "candidate_answer": transcript,
            "audio_b64": audio_b64,
            "qa_log_id": log_id,
            "timestamp": timestamp_iso,
        }
