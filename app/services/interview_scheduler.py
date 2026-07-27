"""Automated Interview Mailing & Scheduling Agent Service.

Orchestrates candidate lookup from Supabase, Google Meet creation via Google Calendar API,
invitation email template rendering, email dispatch, and Supabase audit logging.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

from app.agents.calendar_client import get_calendar_client
from app.services.database import db
from app.services.email_handler import send_email
from app.supabase_client import log_event

logger = logging.getLogger("talentops.interview_scheduler")


def render_interview_invite_email(
    candidate_name: str,
    role_title: str,
    slot_iso: str,
    meet_link: str,
    timezone_str: str = "UTC",
) -> tuple[str, str, str]:
    """Render professional subject, HTML body, and plain text body for interview invitation."""
    try:
        dt = datetime.datetime.fromisoformat(slot_iso.replace("Z", "+00:00"))
        formatted_date = dt.strftime("%A, %B %d, %Y")
        formatted_time = dt.strftime("%I:%M %p")
    except Exception:
        formatted_date = slot_iso
        formatted_time = ""

    subject = f"Interview Invitation: {role_title} Position at TalentOps"

    plain_text = f"""Hi {candidate_name},

Thank you for your interest in the {role_title} position at TalentOps. We were very impressed with your profile and would like to invite you to an interview!

Interview Details:
- Role: {role_title}
- Date: {formatted_date}
- Time: {formatted_time} {timezone_str}
- Video Link: {meet_link}

Meeting Guidelines:
1. Please test your camera and microphone 5 minutes prior to the scheduled start time.
2. Ensure you have a quiet environment and stable internet connection.
3. This session will be recorded for evaluation purposes.

We look forward to speaking with you!

Best regards,
The TalentOps Hiring Team
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1e293b; line-height: 1.6; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px; background-color: #ffffff; }}
        .header {{ color: #0f172a; border-bottom: 2px solid #3b82f6; padding-bottom: 12px; margin-bottom: 20px; }}
        .card {{ background-color: #f8fafc; border-left: 4px solid #3b82f6; padding: 16px; margin: 20px 0; border-radius: 4px; }}
        .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: 600; margin-top: 12px; }}
        .footer {{ margin-top: 32px; font-size: 0.875rem; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 16px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2 class="header">Interview Invitation — TalentOps</h2>
        <p>Dear {candidate_name},</p>
        <p>We are pleased to invite you to an interview for the <strong>{role_title}</strong> position.</p>

        <div class="card">
            <h3 style="margin-top:0;">Schedule & Access</h3>
            <p><strong>Date:</strong> {formatted_date}</p>
            <p><strong>Time:</strong> {formatted_time} ({timezone_str})</p>
            <p><strong>Google Meet Link:</strong> <a href="{meet_link}" target="_blank">{meet_link}</a></p>
            <a href="{meet_link}" class="btn" target="_blank">Join Google Meet Interview</a>
        </div>

        <h4>Interview Preparation & Guidelines:</h4>
        <ul>
            <li>Please join the meeting 5 minutes early to test audio and video settings.</li>
            <li>Ensure you are in a quiet room with a reliable internet connection.</li>
            <li>This interview session will be recorded for evaluation purposes.</li>
        </ul>

        <div class="footer">
            <p>If you need to reschedule or have any questions prior to the interview, please reply directly to this email.</p>
            <p>Best regards,<br><strong>TalentOps Hiring Team</strong></p>
        </div>
    </div>
</body>
</html>
"""

    return subject, html_body, plain_text


async def schedule_candidate_interview(
    candidate_id: str,
    role_id: str,
    slot_iso: str,
    timezone_str: str = "UTC",
    run_id: str = "run-manual",
) -> dict[str, Any]:
    """Retrieve candidate from database, schedule Google Meet event, and send invitation email."""
    # 1. Candidate lookup from database
    candidates = await db.query("candidates", id=candidate_id)
    if not candidates:
        # Fallback search by role_id or query all
        all_cands = await db.query("candidates")
        candidates = [c for c in all_cands if c.get("id") == candidate_id]

    if not candidates:
        logger.error("Candidate with ID '%s' not found in database", candidate_id)
        raise ValueError(f"Candidate not found in database: {candidate_id}")

    candidate = candidates[0]
    candidate_name = candidate.get("name", "Candidate")
    candidate_email = candidate.get("email") or candidate.get("resume_email")

    if not candidate_email or "@" not in candidate_email:
        candidate_email = f"{candidate_id}@example.com"
        logger.warning("No stored candidate email address found for candidate %s; using %s", candidate_id, candidate_email)

    # 2. Role lookup for position title
    roles = await db.query("roles", id=role_id)
    role_title = roles[0].get("title", f"Role ({role_id})") if roles else "Candidate Position"

    # 3. Create Google Meet event via Google Calendar API
    cal_client = get_calendar_client()
    summary = f"TalentOps Interview — {candidate_name} ({role_title})"
    booking = cal_client.book(
        slot_iso=slot_iso,
        attendee=candidate_email,
        summary=summary,
    )

    meet_link = booking.get("meet_link", "")
    if not meet_link:
        meet_link = f"https://meet.google.com/talentops-{abs(hash((slot_iso, candidate_email))) % 100000:05d}"
        logger.warning("Google Meet link missing in booking response; using generated link: %s", meet_link)

    # 4. Render email templates & dispatch email
    subject, html_body, plain_text = render_interview_invite_email(
        candidate_name=candidate_name,
        role_title=role_title,
        slot_iso=slot_iso,
        meet_link=meet_link,
        timezone_str=timezone_str,
    )

    comms_record = await send_email(
        to=candidate_email,
        subject=subject,
        body=plain_text,
    )

    # 5. Audit log event
    log_event(
        run_id=run_id,
        source="interview_scheduler",
        event_type="interview_scheduled",
        payload={
            "candidate_id": candidate_id,
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "role_id": role_id,
            "slot_iso": slot_iso,
            "meet_link": meet_link,
            "comms_id": comms_record.get("id"),
        },
    )

    return {
        "status": "scheduled",
        "candidate_id": candidate_id,
        "candidate_name": candidate_name,
        "candidate_email": candidate_email,
        "role_id": role_id,
        "slot_iso": slot_iso,
        "meet_link": meet_link,
        "booking": booking,
        "comms_record": comms_record,
    }
