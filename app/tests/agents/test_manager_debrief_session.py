"""TDD unit tests for Phase 5 Manager Debrief Agent & Human HR Liaison Session."""
import pytest
from unittest.mock import AsyncMock, patch
from app.agents.manager_debrief import build_manager_debrief_script, create_manager_debrief_session
from app.agents.manager_voice import ManagerVoiceMeeting, REFUSAL
from app.services.vexa_client import VexaClient


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
    final_state = {
        "goal": "Staff AI Architect",
        "top_candidate": "Priya Rao",
        "report": {"decision": "ADVANCE"},
    }
    with patch.object(VexaClient, "join_meeting", new_callable=AsyncMock) as mock_join:
        mock_join.return_value = {"meeting_id": "debrief-meet-1", "status": "joined"}
        res = await create_manager_debrief_session("run-403", final_state)
        assert res["debrief_id"] == "debrief-run-403"
        assert "meet_link" in res
        assert "meet.google.com" in res["meet_link"]
        assert mock_join.called
