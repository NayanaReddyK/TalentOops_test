"""Hybrid Loop Phase 2 (Task 5.6): Extractive Evaluation on the text transcript ONLY.

Structural prosody enforcement (D19): the sole input is the immutable text
transcript from the `interviews` audit trail. No sound, tone, or paralinguistic
signal can reach this module — the text is the blind wall.
"""
import json

from app.services.database import db
from app.services.llm_clients import groq_chat, openrouter_chat

MIN_QUOTE_LEN = 40  # buzzword countermeasure: mechanism/decision/outcome, not name-drops

EXTRACT_PROMPT = (
    "You are an extractive evaluator. From the interview transcript below, extract "
    "verbatim candidate quotes evidencing each rubric competency. A quote qualifies "
    "only if it demonstrates a mechanism, decision, or outcome. Return ONLY a JSON "
    'array: [{"competency_id": str, "quote": str, "speaker": "candidate"}]'
)


def _parse_quotes(raw: str) -> list[dict]:
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        items = json.loads(raw[start:end + 1])
        return [i for i in items if isinstance(i, dict) and i.get("quote")]
    except json.JSONDecodeError:
        return []


class ScorecardAgent:
    def __init__(self, max_retries: int = 2) -> None:
        self.max_retries = max_retries

    async def _extract(self, transcript: str, rubric: dict) -> list[dict]:
        messages = [
            {"role": "system", "content": EXTRACT_PROMPT},
            {"role": "user", "content": json.dumps({
                "rubric": rubric, "transcript": transcript})},
        ]
        try:
            raw = await openrouter_chat(messages, json_mode=True)  # Nemotron primary
        except Exception:
            raw = await groq_chat(messages, json_mode=True)  # Llama 3.3 70B fallback
        return _parse_quotes(raw)

    def _validate(self, transcript: str, item: dict) -> dict | None:
        quote = item["quote"]
        pos = transcript.find(quote)
        if pos == -1 or len(quote) < MIN_QUOTE_LEN:
            return None
        return {"quote": quote, "char_start": pos, "char_end": pos + len(quote),
                "speaker": item.get("speaker", "candidate"), "validated": True}

    async def score(self, interview_id: str, rubric: dict, candidate_id: str) -> dict:
        # INPUT BOUNDARY: text transcript is the one and only evidence source.
        transcript = await db.get_transcript_text(interview_id)
        comps = rubric.get("competencies", [])
        evidence: dict[str, list[dict]] = {c["competency_id"]: [] for c in comps}
        pending = {c["competency_id"] for c in comps}
        for _ in range(self.max_retries + 1):
            if not pending:
                break
            for item in await self._extract(transcript, rubric):
                cid = item.get("competency_id")
                if cid not in evidence:
                    continue
                validated = self._validate(transcript, item)
                if validated and validated["quote"] not in [q["quote"] for q in evidence[cid]]:
                    evidence[cid].append(validated)  # score only after validation
            pending = {cid for cid, quotes in evidence.items() if not quotes}

        level = rubric.get("difficulty_level", "L2")
        competencies, scored = [], 0
        for c in comps:
            quotes = evidence[c["competency_id"]]
            if not quotes:  # no evidence, no score — never inferred
                demonstrated = "insufficient_evidence"
            else:
                demonstrated = level if len(quotes) >= 2 else "L1"
                scored += 1
            competencies.append({"competency_id": c["competency_id"],
                                 "demonstrated_level": demonstrated,
                                 "evidence_quotes": quotes})
        result = {
            "candidate_id": candidate_id,
            "scorecard": {
                "competencies": competencies,
                "overall_fit": scored / len(comps) if comps else 0.0,
                "needs_human_review": scored < len(comps),
            },
        }
        stored = await db.insert("scorecards", {**result, "interview_id": interview_id})
        result["scorecard_id"] = stored["id"]
        return result
