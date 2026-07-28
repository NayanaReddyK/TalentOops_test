"""Tests for Unified Multi-Agent System (Consent Agent, Interview Agent, Evaluator Agent)."""
import pytest
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.agents.consent_agent import ConsentAgent, parse_consent_intent
from app.agents.evaluator_agent import EvaluatorAgent
from app.services.multi_agent_coordinator import MultiAgentCoordinator, RoomSessionState


def test_parse_consent_intent_granted():
    assert parse_consent_intent("Yes, I agree to be recorded.") is True
    assert parse_consent_intent("I give my explicit consent to proceed.") is True
    assert parse_consent_intent("Sure, sounds good.") is True


def test_parse_consent_intent_denied():
    assert parse_consent_intent("No, I do not consent to recording.") is False
    assert parse_consent_intent("I decline.") is False
    assert parse_consent_intent("I am uncomfortable with AI evaluation.") is False


@pytest.mark.asyncio
async def test_consent_agent_process_response_granted():
    agent = ConsentAgent()
    with patch("app.agents.consent_agent.log_event") as mock_log:
        res = await agent.process_response(
            candidate_id="cand-100",
            response_text="Yes, I consent to the recording.",
            room_id="room-123",
            run_id="run-test"
        )
        assert res["consent_granted"] is True
        assert res["status"] == "CONSENT_GRANTED"
        mock_log.assert_called_once()


@pytest.mark.asyncio
async def test_consent_agent_process_response_denied():
    agent = ConsentAgent()
    with patch("app.agents.consent_agent.log_event") as mock_log:
        res = await agent.process_response(
            candidate_id="cand-101",
            response_text="No, I do not want to be recorded.",
            room_id="room-123",
            run_id="run-test"
        )
        assert res["consent_granted"] is False
        assert res["status"] == "CONSENT_DENIED"
        mock_log.assert_called_once()


@pytest.mark.asyncio
async def test_evaluator_agent_evaluate_session():
    evaluator = EvaluatorAgent()
    rubric = {
        "standard": "Python Backend Engineer",
        "competencies": [
            {"competency_id": "python_async", "keywords": ["asyncio", "coroutine", "await"]}
        ],
        "difficulty_level": "L2"
    }
    transcript_turns = [
        {"speaker": "interviewer", "text": "Can you explain how asyncio works in Python?"},
        {"speaker": "candidate", "text": "In Python, asyncio allows non-blocking concurrency using coroutines and the await keyword."}
    ]

    with patch("app.agents.evaluator_agent.db.insert", return_value={"id": "sc-123"}), \
         patch("app.agents.evaluator_agent.upsert_embedding"), \
         patch("app.embeddings.embedder.RemoteEmbedder.embed", return_value=[0.1] * 384), \
         patch("app.embeddings.embedder.RemoteEmbedder.embed_batch", return_value=[[0.1] * 384]):

        scorecard = await evaluator.evaluate_transcript(
            interview_id="iv-cand-100",
            candidate_id="cand-100",
            rubric=rubric,
            transcript_turns=transcript_turns
        )

        assert scorecard["candidate_id"] == "cand-100"
        assert "competencies" in scorecard["scorecard"]
        assert scorecard["scorecard"]["overall_fit"] > 0.0


@pytest.mark.asyncio
async def test_multi_agent_coordinator_flow_consent_granted():
    coord = MultiAgentCoordinator(
        candidate_id="cand-200",
        role_id="role-backend",
        room_id="room-123",
        run_id="run-200"
    )

    rubric = {
        "standard": "Senior Engineer",
        "competencies": [{"competency_id": "system_design", "keywords": ["sharding", "kafka"]}]
    }

    with patch("app.services.multi_agent_coordinator.db.query", side_effect=lambda table, **kw: [rubric] if table == "rubrics" else [{"id": "cand-200", "name": "Sam"}]), \
         patch("app.services.multi_agent_coordinator.ConsentAgent.process_response", return_value={"consent_granted": True, "status": "CONSENT_GRANTED"}), \
         patch("app.services.multi_agent_coordinator.EvaluatorAgent.evaluate_transcript", return_value={"scorecard": {"overall_fit": 0.9}, "scorecard_id": "sc-99"}), \
         patch("app.embeddings.embedder.RemoteEmbedder.embed", return_value=[0.1] * 384), \
         patch("app.embeddings.embedder.RemoteEmbedder.embed_batch", return_value=[[0.1] * 384]):

        res = await coord.run_session(candidate_turns=["I built distributed queues using Kafka."])
        assert res["state"] == RoomSessionState.EVALUATION_COMPLETE.name
        assert res["consent_granted"] is True
        assert "scorecard" in res


@pytest.mark.asyncio
async def test_multi_agent_coordinator_flow_consent_denied():
    coord = MultiAgentCoordinator(
        candidate_id="cand-201",
        role_id="role-backend",
        room_id="room-123",
        run_id="run-201"
    )

    with patch("app.services.multi_agent_coordinator.ConsentAgent.process_response", return_value={"consent_granted": False, "status": "CONSENT_DENIED"}), \
         patch("app.embeddings.embedder.RemoteEmbedder.embed", return_value=[0.1] * 384), \
         patch("app.embeddings.embedder.RemoteEmbedder.embed_batch", return_value=[[0.1] * 384]):

        res = await coord.run_session(candidate_turns=["I refuse recording."])
        assert res["state"] == RoomSessionState.CONSENT_DENIED.name
        assert res["consent_granted"] is False
        assert "Interview terminated early due to consent refusal" in res["message"]
