"""Tests for Interview Mailing & Scheduling Agent (Self-hosted TalentOops Interview Room + Email)."""
import pytest
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.interview_scheduler import schedule_candidate_interview, render_interview_invite_email


def test_render_interview_invite_email():
    candidate_name = "Alex Johnson"
    role_title = "Senior Backend Engineer"
    slot_iso = "2026-08-01T14:00:00Z"
    room_url = "http://localhost:8000/interview/test-room-id"

    subject, html_body, plain_text = render_interview_invite_email(
        candidate_name=candidate_name,
        role_title=role_title,
        slot_iso=slot_iso,
        room_url=room_url,
        timezone_str="UTC"
    )

    assert "Alex Johnson" in plain_text
    assert role_title in subject or role_title in plain_text
    assert room_url in html_body
    assert room_url in plain_text


@pytest.mark.asyncio
async def test_schedule_candidate_interview_success():
    mock_candidate = {"id": "cand-555", "name": "Priya Sharma", "email": "priya.sharma@example.com", "role_id": "role-backend"}

    class _FakeRoom:
        room_id = "r-priya"
        room_url = "http://localhost:8000/interview/r-priya"

    async def _fake_create_room(*args, **kwargs):
        return _FakeRoom()

    with patch("app.services.interview_scheduler.db.query", return_value=[mock_candidate]), \
         patch("app.rooms.room_manager.room_manager.create_room", side_effect=_fake_create_room), \
         patch("app.services.interview_scheduler.send_email") as mock_send_email:

        mock_send_email.return_value = {"id": "comms-123", "status": "sent"}

        result = await schedule_candidate_interview(
            candidate_id="cand-555",
            role_id="role-backend",
            slot_iso="2026-08-05T15:00:00Z",
            timezone_str="UTC"
        )

        assert result["status"] == "scheduled"
        assert result["candidate_email"] == "priya.sharma@example.com"
        assert result["room_url"] == "http://localhost:8000/interview/r-priya"
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

    class _FakeRoom:
        room_id = "r-sam"
        room_url = "http://localhost:8000/interview/r-sam"

    async def _fake_create_room(*args, **kwargs):
        return _FakeRoom()

    with patch("app.services.interview_scheduler.db.query", return_value=[mock_candidate]), \
         patch("app.rooms.room_manager.room_manager.create_room", side_effect=_fake_create_room), \
         patch("app.services.interview_scheduler.send_email") as mock_send_email:

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
            assert data["room_url"] == "http://localhost:8000/interview/r-sam"
