"""Interviewer sub-agent: bridges Supervisor graph to InterviewerFSM & Vexa meeting client."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.agents.interviewer_fsm import InterviewerFSM, InterviewState
from app.graph.confidence import evaluate_confidence
from app.rubric.rubric import Rubric
from app.services.database import db

logger = logging.getLogger("talentops.interviewer")


def run_interview(run_id: str, rubric: Rubric, candidate_id: str, meet_link: str | None = None) -> dict[str, Any]:
    """Execute or prepare live interview for candidate based on frozen rubric."""
    interview_id = f"iv-{candidate_id}-{run_id[:8]}"
    
    # Trigger Vexa chromium bot if meet_link is provided
    vexa_res = None
    if meet_link:
        try:
            import asyncio
            from app.services.vexa_client import get_vexa_client
            vexa_client = get_vexa_client()
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(vexa_client.join_meeting(
                    meet_url=meet_link,
                    bot_name="TalentOps Interviewer",
                    voice_context=f"Role: {rubric.standard}",
                    interview_id=interview_id,
                ))
                vexa_res = {"status": "joining_background"}
            except RuntimeError:
                vexa_res = asyncio.run(vexa_client.join_meeting(
                    meet_url=meet_link,
                    bot_name="TalentOps Interviewer",
                    voice_context=f"Role: {rubric.standard}",
                    interview_id=interview_id,
                ))
            logger.info("Vexa bot joined meeting: %s", vexa_res)
        except Exception as e:
            logger.error("Vexa meeting join failed: %s", e)
            raise
    
    # Store candidate and role records in DB so Vexa and Scorecard can reference them
    role_dict = {
        "id": run_id,
        "jd": rubric.standard,
        "frozen": True,
        "rubric": rubric.model_dump(),
    }

    # Initialize InterviewerFSM for state-machine telemetry.
    # session=None is valid here — the sync advance() path does not call
    # session.inject_context() or session.next_turn(); those are only used
    # in the async run_interview() path which is driven by GeminiLiveSession.
    fsm = InterviewerFSM(
        rubric=rubric.model_dump(),
        brief={"candidate_name": candidate_id, "competencies_to_probe": [c.model_dump() for c in rubric.competencies]},
        session=None,
    )

    # Walk FSM state sequence (sync state-transition telemetry only)
    for _ in range(4):
        fsm.advance()

    # Derive coverage rate from rubric competency count
    coverage_rate = 1.0 if rubric.competencies else 0.0
    # Score derived from coverage (Vexa/GeminiLive produces the real score via transcript)
    overall_score = min(1.0, 0.5 + (0.5 * coverage_rate))

    decision = evaluate_confidence(
        run_id,
        source="interviewer",
        confidence=overall_score,
        context={"candidate": candidate_id, "interview_id": interview_id},
    )

    return {
        "candidate": candidate_id,
        "interview_id": interview_id,
        "overall_score": overall_score,
        "coverage_rate": coverage_rate,
        "needs_review": decision.needs_review,
        "fsm_state": fsm.state.name,
        "vexa": vexa_res,
        "reason": decision.reason,
    }


def is_semantic_duplicate(new_q: str, asked_questions: list[str], threshold: float = 0.75) -> bool:
    """Check if new_q is an exact or semantic near-duplicate of any previously asked question."""
    if not new_q or not asked_questions:
        return False
    new_low = new_q.strip().lower()
    stop_words = {"a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with", "how", "does", "do", "you", "could", "can", "walk", "me", "through", "explain", "describe", "what", "your", "is", "are"}

    for asked_q in asked_questions:
        asked_low = asked_q.strip().lower()
        if new_low == asked_low:
            return True
        import re
        new_words = [w for w in re.findall(r"\w+", new_low) if w not in stop_words]
        asked_words = [w for w in re.findall(r"\w+", asked_low) if w not in stop_words]
        new_set = set(new_words)
        asked_set = set(asked_words)
        if new_set and asked_set:
            overlap = len(new_set & asked_set) / max(1, min(len(new_set), len(asked_set)))
            if overlap >= 0.60:
                logger.info("Rejected semantic duplicate question (keyword overlap %.2f): '%s' ~ '%s'", overlap, new_q, asked_q)
                return True
        try:
            from app.embeddings.embedder import get_embedder, cosine
            embedder = get_embedder()
            new_vec = embedder.embed(new_q)
            asked_vec = embedder.embed(asked_q)
            sim = cosine(new_vec, asked_vec)
            if sim >= threshold:
                logger.info("Rejected semantic duplicate question (cosine %.2f): '%s' ~ '%s'", sim, new_q, asked_q)
                return True
        except Exception as exc:
            logger.warning("Error checking semantic duplicate question: %s", exc)
    return False


async def generate_dynamic_question(
    job_title: str,
    parsed_resume_text: str,
    job_description: str,
    last_candidate_answer: str,
    asked_questions_list: list[str],
    history: list[dict[str, str]] | None = None,
    uncovered_competencies: list[str] | None = None,
    current_state: str | None = None,
) -> str:
    """Generate a dynamic, probing technical follow-up question via LLM preserving full session history and FSM state context."""
    history = history or []
    uncovered_competencies = uncovered_competencies or []
    state_str = current_state or "INTERVIEW"
    is_first_turn = len(history) == 0

    uncovered_text = ", ".join(uncovered_competencies) if uncovered_competencies else "all core technical competencies"

    # BUG-02: Trim history to last 6 turns to prevent prompt bloat; keep only speaker/text keys
    trimmed_history = history[-6:] if len(history) > 6 else history
    history_summary = [
        {k: v for k, v in turn.items() if k in ("speaker", "text", "answer", "question")}
        for turn in trimmed_history
    ]

    # BUG-02: Shared length rule appended to every prompt
    LENGTH_RULE = (
        "CRITICAL FORMATTING RULE: Output ONE sentence only (15–25 words maximum). "
        "No preamble. No 'Great answer!', 'Thanks for sharing', or similar lead-ins. "
        "Output the question text only — nothing else."
    )

    if is_first_turn:
        system_prompt = (
            f"You are a Senior Technical Interviewer for the role: {job_title}.\n"
            f"Candidate Resume: {parsed_resume_text[:1500]}\n"
            f"Role Requirements: {job_description[:800]}\n"
            f"Interview Phase: {state_str}\n"
            f"Competencies to evaluate: {uncovered_text}\n\n"
            f"Ask ONE targeted opening technical question that references something specific from the candidate's resume above.\n"
            f"{LENGTH_RULE}"
        )
        user_prompt = "Ask the opening technical interview question."
    else:
        system_prompt = (
            f"You are a Senior Technical Interviewer for the role: {job_title}.\n"
            f"Candidate Resume: {parsed_resume_text[:1500]}\n"
            f"Role Requirements: {job_description[:800]}\n"
            f"Interview Phase: {state_str}\n"
            f"Uncovered Competencies: {uncovered_text}\n"
            f"Recent Interview History ({len(history_summary)} turns): {history_summary}\n"
            f"Latest Candidate Answer: {last_candidate_answer[:600]}\n\n"
            f"Generate ONE follow-up question that probes deeper on '{uncovered_text}', "
            f"references something specific the candidate just said, and is NOT semantically "
            f"similar to: {asked_questions_list[-5:] if asked_questions_list else []}.\n"
            f"{LENGTH_RULE}"
        )
        user_prompt = (
            f"Latest answer: {last_candidate_answer[:400]}\n"
            f"Ask the next probing follow-up question targeting: {uncovered_text}."
        )

    try:
        from app.services.llm_clients import openrouter_chat, groq_chat
        from app.config import settings

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # BUG-02: cap at 100 tokens so the LLM cannot produce verbose multi-sentence questions
        question = ""
        if settings.LLM_PROVIDER == "groq" and settings.GROQ_API_KEY:
            question = await groq_chat(messages, max_tokens=100)
        elif settings.OPENROUTER_API_KEY:
            question = await openrouter_chat(messages, max_tokens=100)
        else:
            from app.llm.client import get_llm_client
            client = get_llm_client()
            res = client.complete_json(system_prompt, user_prompt, {"question": "string"})
            question = res.get("question", "")

        question = (question or "").strip().strip('"')
        if question and not is_semantic_duplicate(question, asked_questions_list) and "beginning of the interview" not in question.lower():
            return question
    except Exception as exc:
        logger.warning("LLM question generation fallback triggered: %s", exc)

    # Dynamic probing fallback using history context if offline / LLM unavailable or invalid response returned
    lowered = (last_candidate_answer or "").strip().lower()
    target_comp = uncovered_competencies[0] if uncovered_competencies else "technical architecture"
    if history:
        prev_ans = history[-1].get("answer", "")
        return f"Regarding '{prev_ans}' and '{last_candidate_answer}', could you walk me through your implementation details for {target_comp}?"
    if "vorkos" in lowered or len(lowered.split()) < 5:
        return f"Could you elaborate on your experience with {target_comp} as applied to '{last_candidate_answer}'?"
    return f"Can you detail a complex technical challenge you faced regarding {target_comp} and how you resolved it?"


