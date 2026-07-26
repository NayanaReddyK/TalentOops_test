"""TDD unit tests for Phase 3 Headless Vexa Interviewer & Audio Streaming Integration."""
import pytest
from unittest.mock import AsyncMock, patch
from app.agents.interviewer import run_interview
from app.agents.interviewer_fsm import InterviewerFSM, InterviewState
from app.rubric.rubric import Rubric, Competency
from app.graph.nodes import interviewer_node
from app.services.vexa_client import VexaClient


@pytest.fixture
def mock_rubric():
    return Rubric(
        run_id="run-200",
        standard="Senior Software Engineer",
        competencies=[
            Competency(competency_id="system_design", name="System Design", description="Scalable microservices", weight=1.0, keywords=["kafka", "redis"]),
            Competency(competency_id="python", name="Async Python", description="Async Python mastery", weight=1.0, keywords=["asyncio", "fastapi"]),
        ],
    )


def test_interviewer_fsm_8_stage_lifecycle(mock_rubric):
    fsm = InterviewerFSM(
        rubric=mock_rubric.model_dump(),
        brief={"candidate_name": "Priya Rao", "competencies_to_probe": []},
        session=None,
    )
    assert fsm.state == InterviewState.SANDBOX
    fsm.advance()
    assert fsm.state == InterviewState.OPENING
    fsm.advance()
    assert fsm.state == InterviewState.BACKGROUND
    fsm.advance()
    assert fsm.state == InterviewState.PROBING
    fsm.advance()
    assert fsm.state == InterviewState.FOLLOWUPS
    fsm.advance()
    assert fsm.state == InterviewState.RUBRIC_COVERAGE
    fsm.advance()
    assert fsm.state == InterviewState.CLOSING
    fsm.advance()
    assert fsm.state == InterviewState.POST_CALL


def test_run_interview_vexa_integration(mock_rubric):
    with patch.object(VexaClient, "join_meeting", new_callable=AsyncMock) as mock_join:
        mock_join.return_value = {"meeting_id": "vexa-session-1", "status": "joined"}
        res = run_interview("run-201", mock_rubric, "Priya Rao", meet_link="https://meet.google.com/test-meet")
        assert res["candidate"] == "Priya Rao"
        assert "interview_id" in res
        assert res["overall_score"] > 0
        assert mock_join.called


def test_interviewer_node_envelope_output(mock_rubric):
    state = {
        "run_id": "run-202",
        "top_candidate": "Priya Rao",
        "rubric": mock_rubric.model_dump(),
        "completed": ["scheduling"],
        "messages": [],
    }
    result_state = interviewer_node(state)
    assert result_state["stage"] == "EVALUATION"
    assert "interviewer" in result_state["completed"]
    assert len(result_state["messages"]) == 1
    env = result_state["messages"][0]
    assert env["sender"] == "interviewer"
    assert env["recipient"] == "manager"
