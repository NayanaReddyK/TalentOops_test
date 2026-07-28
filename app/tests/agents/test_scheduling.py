"""Integration tests for scheduling agent with self-hosted room creation."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def patch_room_manager(monkeypatch):
    """Prevent actual room creation during tests."""
    import uuid
    from app.rooms import models as room_models

    class _FakeRoom:
        room_id  = str(uuid.uuid4())
        room_url = f"http://localhost:8000/interview/{room_id}"
        candidate_id = "c-test"
        interview_id = "iv-test"
        status   = room_models.RoomStatus.SCHEDULED
        metadata = {}

    class _FakeManager:
        async def create_room(self, *, candidate_id, interview_id, run_id="run", metadata=None):
            r = _FakeRoom()
            r.candidate_id = candidate_id
            r.interview_id = interview_id
            return r

    import app.agents.scheduling as sched_mod
    monkeypatch.setattr(sched_mod, "room_manager", _FakeManager(), raising=False)


class TestSchedulingAgent:
    @pytest.mark.asyncio
    async def test_no_candidate_returns_no_booking(self):
        from app.agents.scheduling import run_scheduling
        with pytest.raises(ValueError, match="No top candidate provided"):
            await run_scheduling(run_id="run-001", top_candidate=None)

    @pytest.mark.asyncio
    async def test_returns_room_url(self, monkeypatch):
        from app.agents.scheduling import run_scheduling
        from unittest.mock import AsyncMock

        mock_db = AsyncMock(return_value=[{"id": "alice-smith", "email": "alice@example.com"}])
        monkeypatch.setattr("app.agents.scheduling.db.query", mock_db)

        result = await run_scheduling(run_id="run-sched", top_candidate="Alice Smith", candidate_email="alice@example.com")
        assert result["status"] == "booked"
        assert "room_url" in result
        assert "room_id" in result
        assert result["candidate_id"] == "alice-smith"
        assert result["candidate_email"] == "alice@example.com"

    @pytest.mark.asyncio
    async def test_candidate_id_normalised(self, monkeypatch):
        from app.agents.scheduling import run_scheduling
        from unittest.mock import AsyncMock

        mock_db = AsyncMock(return_value=[{"id": "john-doe", "email": "john@example.com"}])
        monkeypatch.setattr("app.agents.scheduling.db.query", mock_db)

        result = await run_scheduling(run_id="run-002", top_candidate="John Doe", candidate_email="john@example.com")
        assert result.get("candidate_id") == "john-doe"
        assert result.get("candidate_email") == "john@example.com"
