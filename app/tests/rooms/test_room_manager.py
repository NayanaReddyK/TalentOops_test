"""Tests for RoomManager: create, get, join, broadcast, close."""
from __future__ import annotations

import asyncio
import pytest


@pytest.fixture
def manager():
    """Fresh RoomManager instance for each test (avoids shared state)."""
    from app.rooms.room_manager import RoomManager
    return RoomManager()


@pytest.fixture(autouse=True)
def patch_db(monkeypatch):
    """Mock Supabase DB calls so tests don't need a live database."""
    class _FakeDB:
        async def insert(self, table, data):
            return {"id": "fake-id"}
        async def update(self, table, where, data):
            return {}
        async def query(self, table, **kwargs):
            return []
    import app.rooms.room_manager as mod
    monkeypatch.setattr(mod, "db", _FakeDB())
    # Also silence log_event
    monkeypatch.setattr(mod, "log_event", lambda **kw: None)


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    """Use localhost base URL in tests."""
    from app.config import get_settings
    s = get_settings()
    monkeypatch.setattr(s, "ROOM_BASE_URL", "http://localhost:8000")


class TestRoomManagerCreate:
    @pytest.mark.asyncio
    async def test_create_returns_room(self, manager):
        room = await manager.create_room(
            candidate_id="c-alice",
            interview_id="iv-001",
        )
        assert room.room_id
        assert "localhost:8000/interview/" in room.room_url
        assert room.candidate_id == "c-alice"
        assert room.interview_id == "iv-001"

    @pytest.mark.asyncio
    async def test_created_room_retrievable(self, manager):
        room = await manager.create_room(candidate_id="c-bob", interview_id="iv-002")
        fetched = manager.get_room(room.room_id)
        assert fetched is not None
        assert fetched.room_id == room.room_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_room_returns_none(self, manager):
        assert manager.get_room("does-not-exist") is None


class TestRoomManagerStatus:
    @pytest.mark.asyncio
    async def test_update_status(self, manager):
        from app.rooms.models import RoomStatus
        room = await manager.create_room(candidate_id="c-carol", interview_id="iv-003")
        await manager.update_status(room.room_id, RoomStatus.ACTIVE)
        assert manager.get_room(room.room_id).status == RoomStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_close_room_removes_session(self, manager):
        room = await manager.create_room(candidate_id="c-dave", interview_id="iv-004")
        await manager.close_room(room.room_id)
        assert manager.get_room(room.room_id) is None

    @pytest.mark.asyncio
    async def test_close_nonexistent_room_is_noop(self, manager):
        """Should not raise even if room doesn't exist."""
        await manager.close_room("ghost-room-id")


class TestRoomManagerBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_no_clients_is_noop(self, manager):
        room = await manager.create_room(candidate_id="c-eve", interview_id="iv-005")
        # Should complete without error even with no clients connected
        await manager.broadcast(room.room_id, {"type": "test", "data": {}})


class TestRoomManagerCloseAndEvaluate:
    @pytest.mark.asyncio
    async def test_close_room_evaluates_transcript_and_creates_scorecard(self, manager, monkeypatch):
        """Integration test verifying close_room retrieves interview_qa_logs, runs EvaluatorAgent, and stores scorecard."""
        from unittest.mock import AsyncMock
        from app.rooms.models import RoomStatus

        scorecards_inserted = []
        qa_logs_mock = [
            {
                "question_number": 1,
                "question_text": "Tell me about your Python backend experience.",
                "candidate_answer_transcript": "I built REST APIs with FastAPI and PostgreSQL.",
            },
            {
                "question_number": 2,
                "question_text": "How do you handle scaling and caching?",
                "candidate_answer_transcript": "We used Redis for caching and async handlers.",
            },
        ]

        class _MockDB:
            async def insert(self, table, data):
                if table == "scorecards":
                    scorecards_inserted.append(data)
                    return {"id": "sc-integration-test-123"}
                return {"id": "fake-id"}

            async def update(self, table, where, data):
                return {}

            async def query(self, table, **kwargs):
                if table == "interview_qa_logs":
                    return qa_logs_mock
                if table == "scorecards":
                    return []
                return []

        import app.services.database as db_mod
        mock_db_inst = _MockDB()
        monkeypatch.setattr(db_mod, "db", mock_db_inst)
        import app.rooms.room_manager as rm_mod
        monkeypatch.setattr(rm_mod, "db", mock_db_inst)
        import app.agents.evaluator_agent as eval_mod
        monkeypatch.setattr(eval_mod, "db", mock_db_inst)
        import app.agents.manager_debrief as debrief_mod
        monkeypatch.setattr(debrief_mod, "db", mock_db_inst)

        from unittest.mock import patch
        with patch("app.agents.evaluator_agent.upsert_embedding"):
            room = await manager.create_room(
                candidate_id="cand-eval-test",
                interview_id="iv-eval-test-100",
            )
            res = await manager.close_room(room.room_id)

        assert res["status"] == "EVALUATION_COMPLETE"
        assert "scorecard" in res

        # Assert scorecards table received the inserted payload
        assert len(scorecards_inserted) == 1
        sc_payload = scorecards_inserted[0]
        assert sc_payload["candidate_id"] == "cand-eval-test"
        assert sc_payload["interview_id"] == "iv-eval-test-100"
        assert "overall_fit" in sc_payload["scorecard"]
        assert sc_payload["scorecard"]["overall_fit"] > 0.0
        assert len(sc_payload["detailed_competencies"]) > 0
        assert "final_recommendation" in sc_payload
