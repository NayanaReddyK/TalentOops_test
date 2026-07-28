"""Unit tests verifying fixes for Communication, Evaluator Agent, Manager Debrief, and Scraper/Sourcing."""
from datetime import datetime
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.agents.communication import _invite_body, _decision_body, _address_for, _send, send_invite
from app.agents.evaluator_agent import EvaluatorAgent
from app.agents.manager_debrief import create_manager_debrief_session, process_hr_debrief_turn
from app.agents.manager_voice import ManagerVoiceMeeting, REFUSAL
from app.agents.scraper import Scraper
from app.agents.sourcing import run_sourcing


def test_communication_name_and_copy_fixes():
    # 1. Verify candidate parameter is used instead of huggingface candidate_name
    subject, body = _invite_body("Alice Smith", "10:00 AM", "http://room.url")
    assert "Hi Alice Smith," in body
    assert "huggingface" not in body

    # 2. Verify human readable decision copy
    sub_hire, body_hire = _decision_body("Bob Jones", "STRONG_HIRE")
    assert "Strong Hire — Moving forward to offer stage" in sub_hire
    assert "Strong Hire — Moving forward to offer stage" in body_hire

    sub_rej, body_rej = _decision_body("Bob Jones", "REJECT")
    assert "Application Status Update" in sub_rej

    # 3. Verify address fallback and validation
    addr1 = _address_for("Charlie", "charlie@company.com")
    assert addr1 == "charlie@company.com"

    addr2 = _address_for("David Miller")
    assert addr2 == "david.miller@example.com"


@pytest.mark.asyncio
async def test_communication_idempotency_guard():
    # Mock db to return an existing email_sent event
    mock_events = [{"payload": {"kind": "invite", "to": "alice@example.com", "message_id": "msg-123"}}]
    mock_client = MagicMock()
    mock_client.send.return_value = MagicMock(to="alice@example.com", message_id="msg-456")
    with patch("app.services.database.db.query_sync", return_value=mock_events, create=True), \
         patch("app.services.database.db.query", new_callable=AsyncMock, return_value=mock_events), \
         patch("app.agents.communication.get_email_client", return_value=mock_client):
        res = send_invite("run-100", "Alice", "10:00 AM", candidate_email="alice@example.com")
        assert res.get("skipped") is True
        assert res["message_id"] == "msg-123"


@pytest.mark.asyncio
async def test_evaluator_dynamic_timestamp_and_alert():
    agent = EvaluatorAgent(run_id="run-eval-test")
    
    with patch("app.services.database.db.insert", new_callable=AsyncMock, return_value={"id": "sc-999"}), \
         patch("app.agents.evaluator_agent.upsert_embedding"), \
         patch("app.agents.manager_debrief.create_manager_debrief_session", side_effect=RuntimeError("Debrief creation failed DB down")), \
         patch("app.supabase_client.log_event") as mock_log:
        
        scorecard = await agent.evaluate_transcript(
            interview_id="iv-test-1",
            candidate_id="c-test-1",
            transcript_turns=[{"question": "What is GIL?", "candidate_answer": "Global Interpreter Lock in Python", "competencies": ["python"]}]
        )
        
        evaluated_at = scorecard["final_recommendation"]["evaluated_at"]
        # Ensure timestamp is valid ISO string and non-empty
        assert "T" in evaluated_at
        assert "2026-" in evaluated_at
        
        # Verify alert event logged on debrief creation failure
        mock_log.assert_called_with(
            "run-eval-test", source="evaluator_agent", event_type="debrief_creation_failed",
            payload={"interview_id": "iv-test-1", "candidate_id": "c-test-1", "error": "Debrief creation failed DB down"}
        )


@pytest.mark.asyncio
async def test_manager_debrief_vector_rag_and_session():
    # 1. Test create_manager_debrief_session with explicit candidate ID
    class FakeRoom:
        room_url = "http://localhost/debrief-1"

    with patch("app.services.database.db.query", new_callable=AsyncMock, return_value=[]), \
         patch("app.services.database.db.insert", new_callable=AsyncMock, return_value={"id": "deb-1"}), \
         patch("app.rooms.room_manager.room_manager.create_room", new_callable=AsyncMock, return_value=FakeRoom()):
        session = await create_manager_debrief_session(interview_id="iv-101", candidate_id="c-charlie")
        assert session["candidate_id"] == "c-charlie"

    # 2. Test process_hr_debrief_turn vector RAG
    mock_session = [{
        "knowledge_context": {
            "candidate_id": "c-charlie",
            "final_recommendation": {"hiring_recommendation": "Strong Hire", "overall_suitability_score": 92.0},
            "full_transcript_evaluations": [
                {"question": "How do you scale PostgreSQL?", "candidate_answer": "Using connection pooling and read replicas.", "evaluator_notes": "Demonstrated solid DB knowledge."}
            ]
        }
    }]
    with patch("app.services.database.db.query", new_callable=AsyncMock, return_value=mock_session), \
         patch("app.services.speech_engine.TTSService.synthesize_speech_b64", new_callable=AsyncMock, return_value="mock_audio"), \
         patch("app.services.llm_clients.groq_chat", new_callable=AsyncMock, return_value="The candidate explained database scaling using read replicas."):
        turn_res = await process_hr_debrief_turn("iv-101", "Tell me about PostgreSQL performance")
        assert "response_text" in turn_res


@pytest.mark.asyncio
async def test_manager_voice_regex_and_db_error_handling():
    meeting = ManagerVoiceMeeting(role_id="r-dev")

    # Word boundary regex check: "alteration" should NOT trigger refusal, but "alter" should
    ans_normal = await meeting.answer("What is the candidate's alteration experience?")
    assert "Pipeline state" in ans_normal

    refusal = await meeting.answer("Please alter the scoring pipeline")
    assert refusal == REFUSAL

    # DB Error handling check
    with patch("app.services.database.db.query", side_effect=Exception("Database connection timeout")):
        db_err_ans = await meeting.answer("Show me candidates")
        assert "Database query error" in db_err_ans


def test_scraper_dynamic_skill_extraction():
    scraper = Scraper()
    context = scraper.enrich("https://github.com/candidate", text_content="Senior developer proficient in Python, FastAPI, Docker, and Kubernetes.")
    assert "python" in context["skills"]
    assert "fastapi" in context["skills"]
    assert "docker" in context["skills"]
    assert "kubernetes" in context["skills"]


def test_sourcing_batch_resiliency():
    corpus = [
        {"id": "c1", "text": "Valid resume text with Python skills."},
        {"id": "c2", "text": None}, # Malformed resume text
        {"id": "c3", "text": "Valid resume text with React skills."},
    ]
    with patch("app.agents.sourcing._load_corpus", return_value=corpus), \
         patch("app.agents.sourcing.upsert_embedding"):
        result = run_sourcing("run-sourcing-1", "Find devs", corpus)
        assert result["count"] == 2
        cand_ids = [c["id"] for c in result["candidates"]]
        assert "c1" in cand_ids
        assert "c3" in cand_ids
        assert "c2" not in cand_ids
