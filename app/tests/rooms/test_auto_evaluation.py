"""Tests verifying that EvaluatorAgent automatically triggers upon interview session end."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.rooms.signaling import _InteractiveRoomSession
from app.rooms.models import SignalType


@pytest.mark.asyncio
async def test_session_end_triggers_evaluator_agent_automatically():
    """Verify that sending __END_SESSION__ to _turn_queue triggers EvaluatorAgent and broadcasts evaluation results."""
    mock_ws = AsyncMock()
    session = _InteractiveRoomSession(
        ws=mock_ws,
        room_id="room-test-eval-123",
        interview_id="int-test-123",
        candidate_id="cand-test-123",
        role_id="role-test-123",
        run_id="run-test-123",
    )

    # Add mock transcript turns
    session.transcript = [
        {"speaker": "interviewer", "text": "Tell me about your experience with FastAPI."},
        {"speaker": "candidate", "text": "I built production microservices with FastAPI and PostgreSQL using async handlers."},
    ]
    session.candidate_turns = ["I built production microservices with FastAPI and PostgreSQL using async handlers."]

    # Signal session end immediately
    await session._turn_queue.put("__END_SESSION__")

    broadcast_frames = []

    async def mock_broadcast(room_id, payload):
        broadcast_frames.append(payload)

    with patch("app.rooms.room_manager.room_manager.broadcast", side_effect=mock_broadcast), \
         patch("app.rooms.room_manager.room_manager.close_room", new_callable=AsyncMock), \
         patch("app.services.database.db.query", new_callable=AsyncMock, return_value=[]), \
         patch("app.services.database.db.insert", new_callable=AsyncMock, return_value={"id": "sc-123"}), \
         patch("app.agents.manager_debrief.create_manager_debrief_session", new_callable=AsyncMock):

        await session._interview_loop()

    # Check that broadcast received EVAL_UPDATE and SESSION_END frames with scorecard data
    eval_updates = [f for f in broadcast_frames if f.get("type") == SignalType.EVAL_UPDATE.value]
    session_ends = [f for f in broadcast_frames if f.get("type") == SignalType.SESSION_END.value]

    assert len(eval_updates) == 1
    assert len(session_ends) == 1

    eval_data = eval_updates[0]["data"]
    assert "scorecard" in eval_data
    assert "final_recommendation" in eval_data
    assert "behavioral_metrics" in eval_data
    assert "detailed_competencies" in eval_data
    assert "full_transcript_evaluations" in eval_data

    end_data = session_ends[0]["data"]
    assert end_data["status"] == "completed"
    assert "scorecard" in end_data
    assert "final_recommendation" in end_data
