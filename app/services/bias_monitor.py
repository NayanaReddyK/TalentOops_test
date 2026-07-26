"""Bias guardrails (Task 5.3): protected-attribute detection + prosody policy."""
import re

from app.services.database import db

PROTECTED_ATTRIBUTES: dict[str, list[str]] = {
    "age": ["age", "years old", "born in", "retirement", "too old", "too young"],
    "gender": ["gender", "male", "female", "woman", "man", "nonbinary", "transgender"],
    "religion": ["religion", "church", "mosque", "temple", "synagogue", "muslim",
                 "christian", "hindu", "jewish", "buddhist"],
    "nationality": ["nationality", "citizen", "citizenship", "immigrant", "visa status",
                    "national origin"],
    "ethnicity": ["ethnicity", "race", "racial", "ethnic"],
    "marital_status": ["married", "divorced", "single mother", "single father", "spouse",
                       "husband", "wife"],
    "disability": ["disability", "disabled", "wheelchair", "chronic illness", "medical condition"],
    "sexual_orientation": ["sexual orientation", "gay", "lesbian", "bisexual", "queer"],
    "pregnancy": ["pregnant", "pregnancy", "maternity", "paternity"],
}

STEERING_CUE = (
    "The candidate mentioned a personal/protected topic. Do not acknowledge or probe it; "
    "steer immediately back to job-relevant content and evaluate demonstrated evidence only."
)

PROSODY_KEYS = ("tone", "pitch", "accent", "prosody", "audio", "emotion", "stutter")


class ProsodyViolationError(Exception):
    """A paralinguistic signal reached a scoring payload (forbidden — D16/D19)."""


def assert_no_prosody_inputs(payload: dict) -> None:
    for key, value in payload.items():
        if any(p in str(key).lower() for p in PROSODY_KEYS):
            raise ProsodyViolationError(f"prosody-derived key {key!r} in scoring payload")
        if isinstance(value, dict):
            assert_no_prosody_inputs(value)


class BiasMonitor:
    def __init__(self, interview_id: str | None = None) -> None:
        self.interview_id = interview_id

    def scan(self, text: str) -> list[str]:
        low = text.lower()
        hits = []
        for category, keywords in PROTECTED_ATTRIBUTES.items():
            for kw in keywords:
                if re.search(rf"\b{re.escape(kw)}\b", low):
                    hits.append(category)
                    break
        return hits

    async def handle_turn(self, text: str) -> str | None:
        categories = self.scan(text)
        if not categories:
            return None
        await db.insert("events", {
            "type": "protected_attribute_flag",
            "interview_id": self.interview_id,
            "categories": categories,
            "excerpt": text[:120],
        })
        return STEERING_CUE
