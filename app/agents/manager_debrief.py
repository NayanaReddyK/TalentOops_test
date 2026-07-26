"""Manager AI Debrief Agent: creates a Manager Google Meet link & debriefs the User in real time."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.services.vexa_client import get_vexa_client

logger = logging.getLogger("talentops.manager_debrief")


def build_manager_debrief_script(run_id: str, final_state: dict[str, Any]) -> str:
    """Build the structured voice debriefing script that the Manager AI Agent speaks to the User."""
    goal = final_state.get("goal", "Senior Engineering Position")
    top_cand = final_state.get("top_candidate", "Top Candidate")
    report = final_state.get("report") or {}
    decision = report.get("decision", "ADVANCE")
    shortlist = final_state.get("shortlist") or []

    script = (
        f"Hello! I am your Manager AI Agent. Here is the executive debrief for your hiring run {run_id[:8]}.\n\n"
        f"1. **Sourcing & Drive Ingestion**: We accessed your resumes and evaluated {len(shortlist)} candidates against your goal: '{goal}'.\n"
        f"2. **Screening & Rubric Alignment**: Candidate '{top_cand}' achieved the highest matching score based on our frozen competency standard.\n"
        f"3. **Candidate Interview Outcome**: The Interviewer & Evaluator agents conducted the live interview session. Verbatim evidence quotes were recorded and verified.\n"
        f"4. **Final Decision**: The recommended decision for '{top_cand}' is **{decision}**.\n\n"
        f"I am ready to answer any questions you have regarding candidate competencies, transcript quotes, or fairness metrics."
    )
    return script


async def create_manager_debrief_session(run_id: str, final_state: dict[str, Any]) -> dict[str, Any]:
    """Create a Manager Debrief Meet session and deploy the Manager AI bot."""
    debrief_id = f"debrief-{run_id[:8]}"
    meet_link = f"https://meet.google.com/mgr-{run_id[:4]}-{run_id[4:8]}"

    script = build_manager_debrief_script(run_id, final_state)
    vexa = get_vexa_client()

    try:
        bot_result = await vexa.join_meeting(
            meet_url=meet_link,
            bot_name="Manager AI Debrief Agent",
            voice_context="manager_debrief",
            interview_id=debrief_id,
        )
    except Exception as e:
        logger.error("Vexa bot failed to join Manager Debrief meeting (%s): %s", meet_link, e)
        raise RuntimeError(f"Failed deploying Manager AI Agent to Meet call. Ensure Vexa Bot service is running at '{vexa.base_url}': {e}") from e

    return {
        "debrief_id": debrief_id,
        "meet_link": meet_link,
        "bot_status": bot_result.get("status", "deployed"),
        "script": script,
        "run_id": run_id,
    }
