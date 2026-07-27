"""Scheduling calendar client (Google Calendar API)."""
from __future__ import annotations

import datetime
import logging
from typing import Protocol

logger = logging.getLogger("talentops.calendar")


class CalendarClient(Protocol):
    def find_slots(self, duration_min: int, count: int) -> list[str]:
        ...

    def book(self, slot_iso: str, attendee: str, summary: str) -> dict:
        ...


class MockCalendarClient:
    """Deterministic fixed slots."""

    _SLOTS = [
        "2026-07-25T15:00:00Z",
        "2026-07-25T16:00:00Z",
        "2026-07-26T14:00:00Z",
        "2026-07-26T17:00:00Z",
    ]

    def find_slots(self, duration_min: int, count: int) -> list[str]:
        return self._SLOTS[:count]

    def book(self, slot_iso: str, attendee: str, summary: str) -> dict:
        return {
            "status": "confirmed",
            "event_id": f"mock-{abs(hash((slot_iso, attendee))) % 10_000:04d}",
            "start": slot_iso,
            "attendee": attendee,
            "summary": summary,
            "meet_link": f"https://meet.google.com/talentops-{abs(hash((slot_iso, attendee))) % 10_000:04d}",
        }


class GoogleCalendarClient:
    def __init__(self, token_path: str):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(
            token_path, ["https://www.googleapis.com/auth/calendar"]
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        self._svc = build("calendar", "v3", credentials=creds)

    def find_slots(self, duration_min: int, count: int) -> list[str]:
        now = datetime.datetime.now(datetime.timezone.utc)
        end = now + datetime.timedelta(days=7)

        body = {
            "timeMin": now.isoformat(),
            "timeMax": end.isoformat(),
            "items": [{"id": "primary"}],
        }
        result = self._svc.freebusy().query(body=body).execute()
        busy_periods = result.get("calendars", {}).get("primary", {}).get("busy", [])

        busy_set: set[str] = set()
        for bp in busy_periods:
            start = datetime.datetime.fromisoformat(bp["start"].replace("Z", "+00:00"))
            end_bp = datetime.datetime.fromisoformat(bp["end"].replace("Z", "+00:00"))
            cursor = start
            while cursor < end_bp:
                busy_set.add(cursor.strftime("%Y-%m-%dT%H:00:00Z"))
                cursor += datetime.timedelta(hours=1)

        slots: list[str] = []
        day = now.date() + datetime.timedelta(days=1)
        for d in range(7):
            current_day = day + datetime.timedelta(days=d)
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

    def book(self, slot_iso: str, attendee: str, summary: str) -> dict:
        start_dt = datetime.datetime.fromisoformat(slot_iso.replace("Z", "+00:00"))
        end_dt = start_dt + datetime.timedelta(hours=1)

        event = {
            "summary": summary,
            "description": f"TalentOps AI Interview — {summary}",
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
        from app.services.calendar_service import extract_google_meet_url
        meet_link = extract_google_meet_url(created)
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
    import os

    settings = get_settings()
    if settings.calendar_provider == "mock":
        return MockCalendarClient()

    token_path = settings.google_token_path
    if not os.path.exists(token_path):
        raise FileNotFoundError(
            f"Calendar provider set to '{settings.calendar_provider}' but OAuth token '{token_path}' was not found. "
            f"Please place valid 'token.json' credentials in the project root."
        )

    return GoogleCalendarClient(token_path)
