"""Tests for Oral Interview Agent Engine (Speech STT/TTS + Adaptive Q&A + Supabase Logging)."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.speech_engine import STTService, TTSService
from app.services.conversation_manager import ConversationManager
from app.agents.oral_interview_agent import OralInterviewAgent


@pytest.mark.asyncio
async def test_stt_and_tts_services():
    stt = STTService()
    tts = TTSService()

    with patch.object(stt, "_transcribe_sync", return_value="This is mock transcribed text."), \
         patch.object(tts, "_synthesize_sync", return_value=b"mock_audio_out_123"):
        
        text = await stt.transcribe_audio(b"mock_audio_bytes_123")
        assert isinstance(text, str)
        assert len(text) > 0

        audio_out = await tts.synthesize_speech("What is your experience with Python?")
        assert isinstance(audio_out, bytes)
        assert len(audio_out) > 0


def test_conversation_manager_context_assembly():
    cm = ConversationManager(
        session_id="sess-100",
        job_description="Senior Python Backend Developer with FastAPI experience",
        parsed_resume="Alex Doe. 5 years Python, Postgres, Docker."
    )

    prompt = cm.build_context_prompt()
    assert "Senior Python Backend Developer" in prompt
    assert "Alex Doe" in prompt


@pytest.mark.asyncio
async def test_conversation_manager_adaptive_question_vague_answer():
    cm = ConversationManager(
        session_id="sess-101",
        job_description="Python Architect",
        parsed_resume="Expert in asyncio and GIL"
    )

    # Simulate vague candidate answer
    q1 = await cm.generate_next_question(candidate_text="I used Python for some stuff.")
    assert len(q1) > 0
    assert cm.turn_count == 1
    # Check that follow-up probes deeper due to short/vague answer
    assert "python" in q1.lower() or "detail" in q1.lower() or "probe" in q1.lower() or "experience" in q1.lower() or "specifically" in q1.lower() or "technical" in q1.lower()


@pytest.mark.asyncio
async def test_oral_interview_agent_process_turn():
    agent = OralInterviewAgent()

    with patch("app.agents.oral_interview_agent.db.insert", return_value={"id": "qa-99"}), \
         patch("app.agents.oral_interview_agent.db.query", side_effect=lambda table, **kw: [{"id": "c-1", "resume": "Python engineer"}] if table == "candidates" else [{"jd": "Python Dev"}]), \
         patch("app.services.speech_engine.TTSService.synthesize_speech_b64",
               new_callable=AsyncMock, return_value="bW9jayBhdWRpbyBvdXRwdXQ="):

        res = await agent.process_turn(
            session_id="sess-200",
            candidate_id="cand-200",
            role_id="role-python",
            candidate_text="I designed distributed microservices using FastAPI and Kafka."
        )

        assert res["session_id"] == "sess-200"
        assert res["question_number"] == 1
        assert "question_text" in res
        assert "audio_b64" in res
        assert res["candidate_answer"] == "I designed distributed microservices using FastAPI and Kafka."


@pytest.mark.asyncio
async def test_oral_interview_turn_endpoint():
    with patch("app.agents.oral_interview_agent.OralInterviewAgent.process_turn", return_value={
        "session_id": "sess-300",
        "question_number": 1,
        "question_text": "How do you handle connection pooling in Postgres?",
        "candidate_answer": "We use PgBouncer for connection pooling.",
        "audio_b64": "bW9jayBhdWRpbyBvdXRwdXQ="
    }):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/oral_interview/turn", json={
                "session_id": "sess-300",
                "candidate_id": "cand-300",
                "role_id": "role-backend",
                "candidate_text": "We use PgBouncer for connection pooling."
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["session_id"] == "sess-300"
            assert "PgBouncer" in data["candidate_answer"]
