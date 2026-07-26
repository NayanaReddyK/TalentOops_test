"""Scheduling sub-agent: book an interview slot for the top candidate."""
from __future__ import annotations

import logging
from typing import Any

from app.agents.calendar_client import get_calendar_client

logger = logging.getLogger("talentops.scheduling")


def run_scheduling(run_id: str, top_candidate: str | None, candidate_email: str | None = None, duration_min: int = 45) -> dict[str, Any]:
    client = get_calendar_client()
    slots = client.find_slots(duration_min=duration_min, count=3)

    if not top_candidate or not slots:
        return {"status": "no_booking", "slots": slots, "top_candidate": top_candidate}

    attendee = candidate_email if (candidate_email and "@" in candidate_email) else f"{top_candidate.lower().replace(' ', '.')}@example.com"
    booking = client.book(
        slot_iso=slots[0],
        attendee=attendee,
        summary=f"TalentOps interview — {top_candidate}",
    )
    return {"status": "booked", "offered_slots": slots, "booking": booking}
