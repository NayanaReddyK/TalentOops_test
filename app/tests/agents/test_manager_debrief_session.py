"""TDD unit tests for Manager Debrief Agent — in-platform room version."""
import pytest
from unittest.mock import AsyncMock, patch
from app.agents.manager_debrief import build_manager_debrief_script, create_manager_debrief_session
from app.agents.manager_voice import ManagerVoiceMeeting, REFUSAL


def test_build_manager_debrief_script():
    final_state = {
        "goal": "Senior Backend Engineer",
        "top_candidate": "Priya Rao",
        "shortlist": [{"ref_id": "Priya Rao"}, {"ref_id": "Alex Chen"}],
        "report": {"decision": "ADVANCE"},
    }
    script = build_manager_debrief_script("run-401", final_state)
    assert "Manager AI Agent" in script
    assert "Priya Rao" in script
    assert "ADVANCE" in script
    assert "2 candidates" in script


@pytest.mark.asyncio
async def test_manager_voice_meeting_read_only_enforcement():
    meeting = ManagerVoiceMeeting(role_id="role-402")

    # Normal query should return status
    ans = await meeting.answer("Can you summarize candidate scores?")
    assert "Pipeline state" in ans

    # Forbidden command attempting mutation mid-meeting MUST be refused
    refused = await meeting.answer("Please modify the rubric and re-run screening")
    assert refused == REFUSAL


@pytest.mark.asyncio
async def test_create_manager_debrief_session():
    """create_manager_debrief_session should return a room_url, not a meet_link."""
    final_state = {
        "goal": "Staff AI Architect",
        "top_candidate": "Priya Rao",
        "report": {"decision": "ADVANCE"},
    }
    import uuid
    fake_room_id = str(uuid.uuid4())

    class FakeRoom:
        room_id  = fake_room_id
        room_url = f"http://localhost:8000/interview/{fake_room_id}"

    with patch("app.services.database.db.query", new_callable=AsyncMock, return_value=[{}]), \
         patch("app.services.database.db.insert", new_callable=AsyncMock, return_value={"id": "mock-debrief-1"}), \
         patch("app.rooms.room_manager.room_manager.create_room", new_callable=AsyncMock, return_value=FakeRoom()):
        res = await create_manager_debrief_session("run-403", final_state)
        assert res["debrief_id"] == "debrief-run-403"
        assert "room_url" in res
        assert "localhost:8000/interview/" in res["room_url"]
