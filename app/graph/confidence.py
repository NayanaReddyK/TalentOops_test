"""Confidence thresholding and human-escalation triggers."""
from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings
from app.supabase_client import log_event

NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


@dataclass
class Decision:
    passed: bool
    confidence: float
    needs_review: bool
    reason: str


def evaluate_confidence(
    run_id: str,
    source: str,
    confidence: float,
    *,
    threshold: float | None = None,
    context: dict | None = None,
) -> Decision:
    """Apply the confidence gate and emit an escalation event if triggered."""
    thr = get_settings().confidence_threshold if threshold is None else threshold
    needs_review = confidence < thr
    reason = (
        f"confidence {confidence:.2f} < threshold {thr:.2f}"
        if needs_review
        else f"confidence {confidence:.2f} >= threshold {thr:.2f}"
    )

    if needs_review:
        log_event(
            run_id,
            source=source,
            event_type="escalation",
            payload={"flag": NEEDS_HUMAN_REVIEW, "confidence": confidence, "threshold": thr, **(context or {})},
        )

    return Decision(passed=not needs_review, confidence=confidence, needs_review=needs_review, reason=reason)
