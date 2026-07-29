"""Scheduling calendar client (Google Calendar API).

``MockCalendarClient`` returns deterministic slots/booking so the scheduling
sub-agent runs with no OAuth; ``GoogleCalendarClient`` is the real path built
lazily from OAuth2 credentials.
"""
from __future__ import annotations

import datetime
import logging
from typing import Protocol

logger = logging.getLogger("talentops.calendar")


class CalendarClient(Protocol):
    def find_slots(self, duration_min: int, count: int) -> list[str]:
        ...

    def book(self, slot_iso: str, attendee: str, summary: str, location: str = "", description: str = "") -> dict:
        ...


class MockCalendarClient:
    """Deterministic fixed slots — no network, no OAuth."""

    _SLOTS = [
        "2026-07-15T15:00:00Z",
        "2026-07-15T16:00:00Z",
        "2026-07-16T14:00:00Z",
        "2026-07-16T17:00:00Z",
    ]

    def find_slots(self, duration_min: int, count: int) -> list[str]:
        return self._SLOTS[:count]

    def book(self, slot_iso: str, attendee: str, summary: str, location: str = "", description: str = "") -> dict:
        return {
            "status": "confirmed",
            "event_id": f"mock-{abs(hash((slot_iso, attendee))) % 10_000:04d}",
            "start": slot_iso,
            "attendee": attendee,
            "summary": summary,
            "location": location,
            "description": description,
        }


class GoogleCalendarClient:
    """Real Google Calendar client using OAuth2 token.json."""

    def __init__(self, token_path: str):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(
            token_path, ["https://www.googleapis.com/auth/calendar"]
        )
        # Auto-refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        self._svc = build("calendar", "v3", credentials=creds)

    def find_slots(self, duration_min: int, count: int) -> list[str]:
        """Query FreeBusy for the next 7 days and return available slots."""
        now = datetime.datetime.now(datetime.timezone.utc)
        end = now + datetime.timedelta(days=7)

        body = {
            "timeMin": now.isoformat(),
            "timeMax": end.isoformat(),
            "items": [{"id": "primary"}],
        }
        result = self._svc.freebusy().query(body=body).execute()
        busy_periods = result.get("calendars", {}).get("primary", {}).get("busy", [])
        logger.info("FreeBusy returned %d busy periods", len(busy_periods))

        # Parse busy into a set of blocked hours
        busy_set: set[str] = set()
        for bp in busy_periods:
            start = datetime.datetime.fromisoformat(bp["start"].replace("Z", "+00:00"))
            end_bp = datetime.datetime.fromisoformat(bp["end"].replace("Z", "+00:00"))
            cursor = start
            while cursor < end_bp:
                busy_set.add(cursor.strftime("%Y-%m-%dT%H:00:00Z"))
                cursor += datetime.timedelta(hours=1)

        # Find available 1-hour slots during business hours (9AM-5PM UTC)
        slots: list[str] = []
        day = now.date() + datetime.timedelta(days=1)  # start from tomorrow
        for d in range(7):
            current_day = day + datetime.timedelta(days=d)
            # Skip weekends
            if current_day.weekday() >= 5:
                continue
            for hour in range(9, 17):
                slot_dt = datetime.datetime(
                    current_day.year, current_day.month, current_day.day,
                    hour, 0, 0, tzinfo=datetime.timezone.utc
                )
                slot_iso = slot_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                if slot_iso not in busy_set:
                    slots.append(slot_iso)
                    if len(slots) >= count:
                        return slots
        return slots

    def book(self, slot_iso: str, attendee: str, summary: str, location: str = "", description: str = "") -> dict:
        """Create a real Google Calendar event with the attendee."""
        start_dt = datetime.datetime.fromisoformat(slot_iso.replace("Z", "+00:00"))
        end_dt = start_dt + datetime.timedelta(hours=1)

        event_desc = description if description else f"TalentOps AI Interview — {summary}"
        event = {
            "summary": summary,
            "description": event_desc,
            "location": location,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
            "attendees": [{"email": attendee}],
            "conferenceData": {
                "createRequest": {
                    "requestId": f"talentops-{abs(hash((slot_iso, attendee))) % 100000}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
            "reminders": {"useDefault": True},
        }
        created = (
            self._svc.events()
            .insert(calendarId="primary", body=event, conferenceDataVersion=1)
            .execute()
        )
        meet_link = created.get("hangoutLink", "")
        logger.info("Booked event %s with Meet link: %s", created["id"], meet_link)
        return {
            "status": "confirmed",
            "event_id": created["id"],
            "start": slot_iso,
            "attendee": attendee,
            "summary": summary,
            "meet_link": meet_link,
        }


def get_calendar_client() -> CalendarClient:
    from app.config import get_settings

    settings = get_settings()
    if settings.calendar_provider == "mock":
        return MockCalendarClient()

    # Graceful fallback if token.json doesn't exist yet
    import os
    token_path = settings.google_token_path
    if not os.path.exists(token_path):
        logger.warning(
            "Calendar set to 'google' but %s not found — falling back to MockCalendarClient. "
            "Run: python scripts/auth_google.py",
            token_path,
        )
        return MockCalendarClient()

    return GoogleCalendarClient(token_path)
