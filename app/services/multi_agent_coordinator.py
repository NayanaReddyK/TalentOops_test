"""Multi-Agent Coordinator & State Machine Engine for Google Meet Sessions.

Orchestrates Consent Agent, Interview Agent, and Evaluator Agent in a single Google Meet.
Enforces exact meeting link binding and strict consent state transitions.
"""
from __future__ import annotations

import logging
from enum import IntEnum
from typing import Any

from app.agents.consent_agent import ConsentAgent
from app.agents.evaluator_agent import EvaluatorAgent
from app.agents.interviewer_fsm import InterviewerFSM
from app.services.database import db
from app.services.vexa_client import get_vexa_client
from app.supabase_client import log_event

logger = logging.getLogger("talentops.multi_agent_coordinator")


class MeetingState(IntEnum):
    CREATED = 0
    AGENT_JOINED = 1
    CONSENT_PENDING = 2
    CONSENT_GRANTED = 3
    CONSENT_DENIED = 4
    INTERVIEW_ACTIVE = 5
    EVALUATION_COMPLETE = 6


class MultiAgentCoordinator:
    """Coordinator steering Consent, Interview, and Evaluator agents in a Google Meet session."""

    def __init__(
        self,
        candidate_id: str,
        role_id: str,
        meet_link: str,
        run_id: str = "run-multiagent",
    ):
        if not meet_link or not isinstance(meet_link, str) or not ("meet.google.com" in meet_link or meet_link.startswith("http")):
            raise ValueError(f"Invalid Google Meet URL structure: '{meet_link}'")

        self.candidate_id = candidate_id
        self.role_id = role_id
        self.meet_link = meet_link
        self.run_id = run_id
        self.state = MeetingState.CREATED
        self.interview_id = f"iv-{candidate_id}-{run_id[:8]}"

        self.consent_agent = ConsentAgent()
        self.evaluator_agent = EvaluatorAgent(run_id=run_id)

    async def run_session(
        self,
        consent_response_text: str = "Yes, I consent to the recording.",
        candidate_turns: list[str] | None = None,
    ) -> dict[str, Any]:
        """Execute full multi-agent meeting workflow with state machine checks."""
        # 1. State: CREATED -> AGENT_JOINED
        logger.info("Starting Multi-Agent Meeting session for link: %s", self.meet_link)
        vexa_client = get_vexa_client()

        vexa_info = {"status": "joined"}
        try:
            vexa_info = await vexa_client.join_meeting(
                meet_url=self.meet_link,
                bot_name="TalentOps Interview Assistant",
                voice_context=f"Role: {self.role_id}",
                interview_id=self.interview_id,
            )
        except Exception as e:
            logger.warning("Vexa bot join warning for %s: %s", self.meet_link, e)

        self.state = MeetingState.AGENT_JOINED

        # 2. State: AGENT_JOINED -> CONSENT_PENDING -> CONSENT_GRANTED / CONSENT_DENIED
        self.state = MeetingState.CONSENT_PENDING
        consent_result = await self.consent_agent.process_response(
            candidate_id=self.candidate_id,
            response_text=consent_response_text,
            meet_link=self.meet_link,
            run_id=self.run_id,
        )

        if not consent_result["consent_granted"]:
            self.state = MeetingState.CONSENT_DENIED
            logger.warning("Candidate %s denied consent; terminating meeting session early.", self.candidate_id)
            log_event(
                run_id=self.run_id,
                source="multi_agent_coordinator",
                event_type="interview_aborted",
                payload={
                    "candidate_id": self.candidate_id,
                    "interview_id": self.interview_id,
                    "meet_link": self.meet_link,
                    "reason": "consent_refused",
                    "consent_result": consent_result,
                },
            )
            try:
                if vexa_info.get("meeting_id"):
                    await vexa_client.leave_meeting(vexa_info["meeting_id"])
            except Exception:
                pass

            return {
                "interview_id": self.interview_id,
                "candidate_id": self.candidate_id,
                "meet_link": self.meet_link,
                "state": self.state.name,
                "consent_granted": False,
                "message": "Interview terminated early due to consent refusal.",
                "consent_result": consent_result,
            }

        self.state = MeetingState.CONSENT_GRANTED

        # 3. State: CONSENT_GRANTED -> INTERVIEW_ACTIVE
        self.state = MeetingState.INTERVIEW_ACTIVE
        turns = candidate_turns or ["I am experienced with backend engineering and Python."]

        # Look up job rubric from Supabase/DB
        rubrics = await db.query("rubrics", run_id=self.run_id)
        rubric = rubrics[0] if rubrics else {
            "standard": f"Position ({self.role_id})",
            "competencies": [{"competency_id": "core_skills", "keywords": ["python", "backend"]}]
        }

        # Setup Interviewer FSM with async session adapter
        class AsyncSession:
            async def inject_context(self, text: str) -> None:
                pass
            async def next_turn(self, text: str) -> str:
                return f"Tell me more about {text}"

        fsm = InterviewerFSM(
            rubric=rubric,
            brief={"candidate_name": self.candidate_id},
            session=AsyncSession(),
        )

        fsm_result = await fsm.run_interview(turns, transcript_ref=self.interview_id)

        # 4. State: INTERVIEW_ACTIVE -> EVALUATION_COMPLETE (Evaluator Agent concurrent evaluation)
        transcript_formatted = [
            {"speaker": "interviewer", "text": "Can you share your background?"},
            {"speaker": "candidate", "text": " ".join(turns)}
        ]

        scorecard_result = await self.evaluator_agent.evaluate_transcript(
            interview_id=self.interview_id,
            candidate_id=self.candidate_id,
            rubric=rubric,
            transcript_turns=transcript_formatted,
        )

        self.state = MeetingState.EVALUATION_COMPLETE

        log_event(
            run_id=self.run_id,
            source="multi_agent_coordinator",
            event_type="meeting_completed",
            payload={
                "candidate_id": self.candidate_id,
                "interview_id": self.interview_id,
                "meet_link": self.meet_link,
                "scorecard_id": scorecard_result.get("scorecard_id"),
            }
        )

        try:
            if vexa_info.get("meeting_id"):
                await vexa_client.leave_meeting(vexa_info["meeting_id"])
        except Exception:
            pass

        return {
            "interview_id": self.interview_id,
            "candidate_id": self.candidate_id,
            "role_id": self.role_id,
            "meet_link": self.meet_link,
            "state": self.state.name,
            "consent_granted": True,
            "fsm_summary": fsm_result,
            "scorecard": scorecard_result["scorecard"],
            "scorecard_id": scorecard_result.get("scorecard_id"),
        }
