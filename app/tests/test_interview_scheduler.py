"""Tests for Interview Mailing & Scheduling Agent (Google Calendar Meet + Supabase + Email)."""
import pytest
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.calendar_service import extract_google_meet_url
from app.services.interview_scheduler import schedule_candidate_interview, render_interview_invite_email


def test_extract_google_meet_url_from_entry_points():
    sample_response = {
        "id": "event_123",
        "hangoutLink": "https://hangouts.google.com/legacy",
        "conferenceData": {
            "entryPoints": [
                {"entryPointType": "video", "uri": "https://meet.google.com/abc-defg-hij"},
                {"entryPointType": "phone", "uri": "tel:+1-555-0100"}
            ]
        }
    }
    url = extract_google_meet_url(sample_response)
    assert url == "https://meet.google.com/abc-defg-hij"


def test_extract_google_meet_url_fallback_hangout_link():
    sample_response = {
        "id": "event_456",
        "hangoutLink": "https://meet.google.com/xyz-uvwx-rst"
    }
    url = extract_google_meet_url(sample_response)
    assert url == "https://meet.google.com/xyz-uvwx-rst"


def test_render_interview_invite_email():
    candidate_name = "Alex Johnson"
    role_title = "Senior Backend Engineer"
    slot_iso = "2026-08-01T14:00:00Z"
    meet_link = "https://meet.google.com/test-meet-link"

    subject, html_body, plain_text = render_interview_invite_email(
        candidate_name=candidate_name,
        role_title=role_title,
        slot_iso=slot_iso,
        meet_link=meet_link,
        timezone_str="UTC"
    )

    assert "Alex Johnson" in plain_text
    assert role_title in subject or role_title in plain_text
    assert meet_link in html_body
    assert meet_link in plain_text


@pytest.mark.asyncio
async def test_schedule_candidate_interview_success():
    mock_candidate = {"id": "cand-555", "name": "Priya Sharma", "email": "priya.sharma@example.com", "role_id": "role-backend"}
    mock_booking = {
        "status": "confirmed",
        "event_id": "gcal-evt-99",
        "start": "2026-08-05T15:00:00Z",
        "attendee": "priya.sharma@example.com",
        "meet_link": "https://meet.google.com/priya-interview-meet"
    }

    with patch("app.services.interview_scheduler.db.query", return_value=[mock_candidate]), \
         patch("app.services.interview_scheduler.get_calendar_client") as mock_get_cal, \
         patch("app.services.interview_scheduler.send_email") as mock_send_email:

        mock_cal = MagicMock()
        mock_cal.book.return_value = mock_booking
        mock_get_cal.return_value = mock_cal
        mock_send_email.return_value = {"id": "comms-123", "status": "sent"}

        result = await schedule_candidate_interview(
            candidate_id="cand-555",
            role_id="role-backend",
            slot_iso="2026-08-05T15:00:00Z",
            timezone_str="UTC"
        )

        assert result["status"] == "scheduled"
        assert result["candidate_email"] == "priya.sharma@example.com"
        assert result["meet_link"] == "https://meet.google.com/priya-interview-meet"
        mock_send_email.assert_called_once()


@pytest.mark.asyncio
async def test_schedule_candidate_interview_candidate_not_found():
    with patch("app.services.interview_scheduler.db.query", return_value=[]):
        with pytest.raises(ValueError, match="Candidate not found"):
            await schedule_candidate_interview(
                candidate_id="non-existent",
                role_id="role-1",
                slot_iso="2026-08-05T15:00:00Z"
            )


@pytest.mark.asyncio
async def test_schedule_interview_endpoint():
    mock_candidate = {"id": "cand-777", "name": "Sam Lee", "email": "sam.lee@example.com", "role_id": "role-ml"}
    mock_booking = {
        "status": "confirmed",
        "event_id": "evt-777",
        "meet_link": "https://meet.google.com/sam-meet-link"
    }

    with patch("app.services.interview_scheduler.db.query", return_value=[mock_candidate]), \
         patch("app.services.interview_scheduler.get_calendar_client") as mock_get_cal, \
         patch("app.services.interview_scheduler.send_email") as mock_send_email:

        mock_cal = MagicMock()
        mock_cal.book.return_value = mock_booking
        mock_get_cal.return_value = mock_cal
        mock_send_email.return_value = {"id": "c-777", "status": "sent"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/schedule_interview", json={
                "candidate_id": "cand-777",
                "role_id": "role-ml",
                "slot_iso": "2026-08-10T10:00:00Z",
                "timezone": "UTC"
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "scheduled"
            assert data["meet_link"] == "https://meet.google.com/sam-meet-link"
