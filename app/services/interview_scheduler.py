"""Automated Interview Mailing & Scheduling Service.

Orchestrates candidate lookup from Supabase, self-hosted room creation,
invitation email rendering and dispatch, and audit logging.

Google Calendar API and Google Meet have been fully removed.
Interview rooms are created via app.rooms.room_manager.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

from app.services.database import db
from app.services.email_handler import send_email
from app.supabase_client import log_event

logger = logging.getLogger("talentops.interview_scheduler")


def render_interview_invite_email(
    candidate_name: str,
    role_title: str,
    slot_iso: str,
    room_url: str,
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

    subject = f"Interview Invitation: {role_title} Position at TalentOops"

    plain_text = f"""Hi {candidate_name},

Thank you for your interest in the {role_title} position at TalentOops. We were very impressed with your profile and would like to invite you to an interview!

Interview Details:
- Role: {role_title}
- Date: {formatted_date}
- Time: {formatted_time} {timezone_str}
- Interview Room: {room_url}

How to Join:
1. Click the interview room link above at your scheduled time — no additional software needed.
2. Allow microphone and camera access when prompted.
3. Ensure you are in a quiet room with a reliable internet connection.
4. This session will be recorded for evaluation purposes; you will confirm consent at the start.

We look forward to speaking with you!

Best regards,
The TalentOops Hiring Team
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1e293b; line-height: 1.6; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px; background-color: #ffffff; }}
        .header {{ color: #0f172a; border-bottom: 2px solid #06b6d4; padding-bottom: 12px; margin-bottom: 20px; }}
        .card {{ background-color: #f0fdfa; border-left: 4px solid #06b6d4; padding: 16px; margin: 20px 0; border-radius: 4px; }}
        .btn {{ display: inline-block; background: linear-gradient(135deg, #0891b2, #06b6d4); color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: 600; margin-top: 12px; }}
        .footer {{ margin-top: 32px; font-size: 0.875rem; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 16px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2 class="header">Interview Invitation — TalentOops</h2>
        <p>Dear {candidate_name},</p>
        <p>We are pleased to invite you to an interview for the <strong>{role_title}</strong> position.</p>

        <div class="card">
            <h3 style="margin-top:0;">Schedule &amp; Access</h3>
            <p><strong>Date:</strong> {formatted_date}</p>
            <p><strong>Time:</strong> {formatted_time} ({timezone_str})</p>
            <p><strong>Interview Room:</strong> <a href="{room_url}" target="_blank">{room_url}</a></p>
            <a href="{room_url}" class="btn" target="_blank">Join TalentOops Interview Room</a>
        </div>

        <h4>Interview Preparation &amp; Guidelines:</h4>
        <ul>
            <li>Click the room link 2–3 minutes before your scheduled time.</li>
            <li>Allow microphone and camera permissions when the browser requests them.</li>
            <li>Ensure you are in a quiet environment with a reliable internet connection.</li>
            <li>This interview session will be recorded for evaluation purposes.</li>
        </ul>

        <div class="footer">
            <p>If you need to reschedule or have any questions, please reply directly to this email.</p>
            <p>Best regards,<br><strong>TalentOops Hiring Team</strong></p>
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
    """Retrieve candidate from database, create a TalentOops interview room, and send invitation email."""
    # 1. Candidate lookup from database
    candidates = await db.query("candidates", id=candidate_id)
    if not candidates:
        all_cands = await db.query("candidates")
        candidates = [c for c in all_cands if c.get("id") == candidate_id]

    if not candidates:
        logger.error("Candidate with ID '%s' not found in database", candidate_id)
        raise ValueError(f"Candidate not found in database: {candidate_id}")

    candidate       = candidates[0]
    candidate_name  = candidate.get("name", "Candidate")
    candidate_email = candidate.get("email") or candidate.get("resume_email")

    if not candidate_email or "@" not in candidate_email:
        candidate_email = f"{candidate_id}@example.com"
        logger.warning(
            "No stored candidate email for %s; using placeholder %s",
            candidate_id, candidate_email,
        )

    # 2. Role lookup for position title
    roles      = await db.query("roles", id=role_id)
    role_title = roles[0].get("title", f"Role ({role_id})") if roles else "Candidate Position"

    # 3. Create a self-hosted interview room (replaces Google Calendar / Meet)
    from app.rooms.room_manager import room_manager
    room = await room_manager.create_room(
        candidate_id=candidate_id,
        interview_id=f"iv-{candidate_id}-{run_id[:8]}",
        run_id=run_id,
        metadata={
            "role_id": role_id,
            "slot_iso": slot_iso,
            "timezone": timezone_str,
            "candidate_email": candidate_email,
        },
    )
    room_url = room.room_url

    # 4. Render email templates and dispatch invitation
    subject, html_body, plain_text = render_interview_invite_email(
        candidate_name=candidate_name,
        role_title=role_title,
        slot_iso=slot_iso,
        room_url=room_url,
        timezone_str=timezone_str,
    )

    comms_record = await send_email(
        to=candidate_email,
        subject=subject,
        body=plain_text,
    )

    # 5. Audit log
    log_event(
        run_id=run_id,
        source="interview_scheduler",
        event_type="interview_scheduled",
        payload={
            "candidate_id":    candidate_id,
            "candidate_name":  candidate_name,
            "candidate_email": candidate_email,
            "role_id":         role_id,
            "slot_iso":        slot_iso,
            "room_id":         room.room_id,
            "room_url":        room_url,
            "comms_id":        comms_record.get("id"),
        },
    )

    return {
        "status":          "scheduled",
        "candidate_id":    candidate_id,
        "candidate_name":  candidate_name,
        "candidate_email": candidate_email,
        "role_id":         role_id,
        "slot_iso":        slot_iso,
        "room_id":         room.room_id,
        "room_url":        room_url,
        "comms_record":    comms_record,
    }
