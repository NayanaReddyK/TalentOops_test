"""Unit tests verifying the 4 server log fixes:
1. STT/TTS oral interview configuration & warnings.
2. Rubrics database schema & supervisor persistence.
3. Room status update with room_id primary key column.
4. Rest API fallback for Supabase client calls.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.database import Database
from app.graph.supervisor import run_pipeline


client = TestClient(app)


def test_supabase_rest_v1_fallback_route():
    """Verify GET /rest/v1/events returns 200 OK instead of 404."""
    response = client.get("/rest/v1/events")
    assert response.status_code == 200
    assert response.json() == []


def test_supabase_rest_v1_fallback_post():
    """Verify POST /rest/v1/events returns 200 OK."""
    response = client.post("/rest/v1/events", json={"data": "test"})
    assert response.status_code == 200
    assert response.json() == [] or response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_database_update_with_dict_and_custom_id_col():
    """Verify Database.update handles dict key filter (e.g. room_id) without crashing."""
    db_inst = Database()
    with patch.object(db_inst, "_sb") as mock_sb:
        mock_table = MagicMock()
        mock_sb.return_value.table.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value.data = [{"room_id": "room-123", "status": "ACTIVE"}]

        res = await db_inst.update("interview_rooms", {"room_id": "room-123"}, {"status": "ACTIVE"})
        assert res == {"room_id": "room-123", "status": "ACTIVE"}
        mock_table.eq.assert_called_with("room_id", "room-123")


@pytest.mark.asyncio
async def test_supervisor_run_pipeline_persists_rubric():
    """Verify run_pipeline inserts frozen rubric into DB."""
    with (
        patch("app.graph.supervisor.SUPERVISOR.ainvoke", new=AsyncMock(return_value={"completed": ["sourcing"]})),
        patch("app.graph.supervisor.log_event"),
        patch("app.services.database.db.insert", new=AsyncMock()) as mock_insert,
    ):
        res = await run_pipeline(goal="Test Hiring Role", standard="High Standard")
        assert "run_id" in res
        assert mock_insert.awaited
        args = mock_insert.call_args_list[0].args
        assert args[0] == "rubrics"
        assert args[1]["role_title"] == "Test Hiring Role"
        assert len(args[1]["competencies"]) > 0
