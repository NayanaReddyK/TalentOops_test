"""Google Calendar Service for Google Meet event management (Google Calendar API v3)."""
from __future__ import annotations

import datetime
import logging
import os
from typing import Any

logger = logging.getLogger("talentops.calendar_service")


def extract_google_meet_url(event_data: dict[str, Any]) -> str:
    """Extract dynamically generated Google Meet URL from Google Calendar API v3 event data.
    
    Checks conferenceData.entryPoints for entryPointType == 'video' first,
    then falls back to hangoutLink if available.
    """
    if not event_data:
        return ""

    conf_data = event_data.get("conferenceData", {})
    entry_points = conf_data.get("entryPoints", [])
    for ep in entry_points:
        if ep.get("entryPointType") == "video" and ep.get("uri"):
            return ep["uri"]

    if event_data.get("hangoutLink"):
        return event_data["hangoutLink"]

    return ""


class GoogleCalendarService:
    """Service layer managing Google Calendar API operations."""

    def __init__(self, token_path: str | None = None):
        from app.config import get_settings
        settings = get_settings()
        self.token_path = token_path or settings.google_token_path
        self._svc = None

    def _get_service(self):
        if self._svc is not None:
            return self._svc

        if not os.path.exists(self.token_path):
            raise FileNotFoundError(
                f"Google OAuth credentials token file not found at '{self.token_path}'. "
                f"Please ensure a valid token file is provided."
            )

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = Credentials.from_authorized_user_file(
                self.token_path, ["https://www.googleapis.com/auth/calendar"]
            )
            if creds.expired and creds.refresh_token:
                logger.info("Refreshing expired Google Calendar OAuth credentials")
                creds.refresh(Request())
            self._svc = build("calendar", "v3", credentials=creds)
            return self._svc
        except Exception as e:
            logger.error("Failed to initialize Google Calendar API service: %s", e)
            raise RuntimeError(f"Google Calendar API initialization error: {e}") from e

    def create_interview_meeting(
        self,
        summary: str,
        start_iso: str,
        attendee_email: str,
        duration_minutes: int = 60,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a Google Meet event programmatically via Google Calendar API v3 conferenceData."""
        svc = self._get_service()
        start_dt = datetime.datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)

        request_id = f"meet-{abs(hash((start_iso, attendee_email))) % 1_000_000:06d}"

        event_body = {
            "summary": summary,
            "description": description or f"Interview Session — {summary}",
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
            "attendees": [{"email": attendee_email}],
            "conferenceData": {
                "createRequest": {
                    "requestId": request_id,
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
            "reminders": {"useDefault": True},
        }

        try:
            created_event = (
                svc.events()
                .insert(calendarId="primary", body=event_body, conferenceDataVersion=1)
                .execute()
            )
            meet_link = extract_google_meet_url(created_event)
            return {
                "status": "confirmed",
                "event_id": created_event.get("id"),
                "start": start_iso,
                "attendee": attendee_email,
                "summary": summary,
                "meet_link": meet_link,
                "raw_event": created_event,
            }
        except Exception as e:
            logger.error("Failed to create Google Calendar Meet event for %s: %s", attendee_email, e)
            raise RuntimeError(f"Google Calendar event creation failed: {e}") from e
