"""Reporting sub-agent: synthesizes run summary, scorecards, & candidate outcome decision."""
from __future__ import annotations

import logging
from typing import Any

from app.agents.communication import send_decision, send_rejection

logger = logging.getLogger("talentops.reporting")


def run_reporting(run_id: str, state: dict[str, Any]) -> dict[str, Any]:
    shortlist = state.get("shortlist") or []
    top = state.get("top_candidate")
    interview = (state.get("results") or {}).get("interview") or {}
    needs_review = state.get("needs_review", False) or interview.get("needs_review", False)

    emails_sent = []
    if top:
        if needs_review:
            decision = "HOLD_FOR_REVIEW"
            email = send_decision(run_id, top, decision)
            emails_sent.append(email)
        else:
            decision = "ADVANCE"
            email = send_decision(run_id, top, decision)
            emails_sent.append(email)

    for item in shortlist:
        cid = item.get("ref_id")
        if cid and cid != top:
            rej = send_rejection(run_id, cid)
            emails_sent.append(rej)

    return {
        "run_id": run_id,
        "goal": state.get("goal"),
        "top_candidate": top,
        "decision": decision if top else "NO_CANDIDATES",
        "needs_human_review": needs_review,
        "shortlist_count": len(shortlist),
        "emails_sent": emails_sent,
    }
