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
    class _FakeSettings:
        ROOM_BASE_URL = "http://localhost:8000"
    import app.config as cfg_mod
    monkeypatch.setattr(cfg_mod, "get_settings", lambda: _FakeSettings())


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
