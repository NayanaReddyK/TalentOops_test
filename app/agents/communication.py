"""Communication capability: candidate-facing emails."""
from __future__ import annotations

import logging
from typing import Any

from app.agents.email_client import get_email_client
from app.supabase_client import log_event

logger = logging.getLogger("talentops.communication")


def _invite_body(candidate: str, slot: str, meet_link: str | None = None) -> tuple[str, str]:
    subject = "Interview invitation — next steps"
    meet_info = f"Google Meet Link: {meet_link}\n" if meet_link else ""
    body = (
        f"Hi {candidate},\n\n"
        f"Thank you for your application. We'd like to invite you to an interview.\n"
        f"Proposed time: {slot}.\n"
        f"{meet_info}\n"
        f"This session will be recorded for evaluation; consent will be confirmed "
        f"at the start of the call.\n\n"
        f"Best regards,\nThe Hiring Team"
    )
    return subject, body


def _rejection_body(candidate: str) -> tuple[str, str]:
    subject = "Update on your application"
    body = (
        f"Hi {candidate},\n\n"
        f"Thank you for taking the time to apply. After careful review against a "
        f"consistent evaluation standard, we won't be moving forward at this time.\n\n"
        f"We wish you the best in your search.\n\nRegards,\nThe Hiring Team"
    )
    return subject, body


def _decision_body(candidate: str, decision: str) -> tuple[str, str]:
    subject = f"Interview outcome — {decision}"
    body = (
        f"Hi {candidate},\n\n"
        f"Following your interview, the current outcome is: {decision}.\n\n"
        f"Regards,\nThe Hiring Team"
    )
    return subject, body


from app.services.email_handler import _dispatch_smtp_email


def _address_for(candidate: str, candidate_email: str | None = None) -> str:
    if candidate_email and "@" in candidate_email:
        return candidate_email
    if "@" in candidate:
        return candidate
    return f"{candidate}@example.com"


def _send(run_id: str, kind: str, candidate: str, subject: str, body: str, candidate_email: str | None = None) -> dict[str, Any]:
    client = get_email_client()
    target_address = _address_for(candidate, candidate_email)
    msg = client.send(to=target_address, subject=subject, body=body)

    # Attempt real SMTP dispatch if configured
    from app.config import settings
    if settings.SMTP_SERVER and not settings.is_offline_mode:
        _dispatch_smtp_email(target_address, subject, body)

    log_event(
        run_id, source="communication", event_type="email_sent",
        payload={"kind": kind, "to": msg.to, "subject": subject, "message_id": msg.message_id},
    )
    return {"kind": kind, "to": msg.to, "message_id": msg.message_id, "subject": subject}


def send_invite(run_id: str, candidate: str, slot: str, meet_link: str | None = None, candidate_email: str | None = None) -> dict[str, Any]:
    subject, body = _invite_body(candidate, slot, meet_link)
    return _send(run_id, "invite", candidate, subject, body, candidate_email)


def send_rejection(run_id: str, candidate: str, candidate_email: str | None = None) -> dict[str, Any]:
    subject, body = _rejection_body(candidate)
    return _send(run_id, "rejection", candidate, subject, body, candidate_email)


def send_decision(run_id: str, candidate: str, decision: str, candidate_email: str | None = None) -> dict[str, Any]:
    subject, body = _decision_body(candidate, decision)
    return _send(run_id, "decision", candidate, subject, body, candidate_email)
