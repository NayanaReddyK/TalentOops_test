"""Async per-candidate interview brief via Groq Llama 3.3 70B (Task 4.5)."""
import asyncio
import json

from app.services.database import db
from app.services.llm_clients import groq_chat

PROMPT = (
    "You are preparing an interviewer. From the job description, frozen rubric, "
    "resume, and screening notes below, return ONLY JSON: "
    '{"competencies_to_probe": [{"competency_id": str, "depth": str, "rationale": str}], '
    '"resume_claims_to_verify": [str], "gaps_to_probe": [str]}'
)


def _parse_json_block(text: str) -> dict | None:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start:end + 1])
        return parsed if isinstance(parsed, dict) and "competencies_to_probe" in parsed else None
    except json.JSONDecodeError:
        return None


def _fallback_brief(rubric: dict) -> dict:
    comps = rubric.get("competencies", [])
    return {
        "competencies_to_probe": [
            {"competency_id": c.get("competency_id", ""), "depth": "standard",
             "rationale": "fallback: probe rubric competency directly"} for c in comps],
        "resume_claims_to_verify": [],
        "gaps_to_probe": [],
    }


async def generate_brief(role_id: str, candidate_id: str, jd: str, rubric: dict,
                         resume: str, screening_notes: str = "") -> dict:
    messages = [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": json.dumps({
            "jd": jd, "rubric": rubric, "resume": resume,
            "screening_notes": screening_notes})},
    ]
    raw = None
    for attempt in range(3):  # retry/backoff for Groq RPM limits
        try:
            raw = await groq_chat(messages, json_mode=True)
            break
        except Exception as e:
            if attempt == 2:
                raise e
            await asyncio.sleep(0.01 * 2**attempt)
    brief = _parse_json_block(raw) if raw else None
    if brief is None:
        raise RuntimeError("Failed to generate or parse interview brief from LLM API")
    return await db.insert("briefs", {
        "role_id": role_id, "candidate_id": candidate_id, "brief": brief})


async def on_candidate_scheduled(event: dict) -> dict:
    role = await db.get("roles", event["role_id"]) or {}
    candidate = await db.get("candidates", event["candidate_id"]) or {}
    return await generate_brief(
        role_id=event["role_id"], candidate_id=event["candidate_id"],
        jd=role.get("jd", ""), rubric=role.get("rubric", {}),
        resume=candidate.get("resume", ""),
        screening_notes=candidate.get("screening_notes", ""))
