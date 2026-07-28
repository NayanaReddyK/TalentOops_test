"""Tests for Manager Agent Post-Interview HR Debrief System."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.manager_debrief import create_manager_debrief_session, process_hr_debrief_turn
from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_create_manager_debrief_session():
    mock_scorecard = [
        {
            "interview_id": "iv-alex-99",
            "candidate_id": "c-alex",
            "scorecard": {"overall_fit": 0.88},
            "behavioral_metrics": {"confidence_level": 0.90},
            "detailed_competencies": [{"competency_id": "async_python", "technical_accuracy": 92.0}],
            "full_transcript_evaluations": [
                {
                    "question_number": 1,
                    "question": "Explain async Python?",
                    "candidate_answer": "Async Python uses asyncio event loops.",
                    "confidence_score": 0.9,
                    "evaluator_notes": "Strong technical accuracy."
                }
            ],
            "final_recommendation": {"hiring_recommendation": "Strong Hire", "overall_suitability_score": 88.0}
        }
    ]

    mock_db_insert = {"id": "debrief-uuid-123"}
    with patch("app.services.database.db.query", new_callable=AsyncMock, return_value=mock_scorecard), \
         patch("app.services.database.db.insert", new_callable=AsyncMock, return_value=mock_db_insert):
        res = await create_manager_debrief_session(
            interview_id="iv-alex-99",
            candidate_id="c-alex"
        )

        assert res["interview_id"] == "iv-alex-99"
        assert res["candidate_id"] == "c-alex"
        assert "room_url" in res
        assert res["status"] in ["Manager Agent Waiting", "Scheduled"]
        assert "knowledge_context" in res
        assert res["knowledge_context"]["candidate_id"] == "c-alex"


@pytest.mark.asyncio
async def test_process_hr_debrief_turn():
    knowledge_context = {
        "candidate_id": "c-alex",
        "interview_id": "iv-alex-99",
        "final_recommendation": {
            "hiring_recommendation": "Strong Hire",
            "overall_suitability_score": 88.0,
            "executive_summary": "Strong candidate."
        },
        "full_transcript_evaluations": [
            {
                "question_number": 1,
                "question": "How do you handle SQL query optimization?",
                "candidate_answer": "I use vector indexes and PgBouncer connection pooling.",
                "evaluator_notes": "Demonstrated deep database expertise."
            }
        ]
    }

    mock_session = [
        {
            "id": "db-1",
            "interview_id": "iv-alex-99",
            "candidate_id": "c-alex",
            "meet_link": "https://meet.google.com/abc-defg-hij",
            "status": "In Progress",
            "knowledge_context": knowledge_context
        }
    ]

    with patch("app.services.database.db.query", new_callable=AsyncMock, return_value=mock_session), \
         patch("app.services.speech_engine.TTSService.synthesize_speech_b64",
               new_callable=AsyncMock, return_value="bW9jayBhdWRpbyBvdXRwdXQ="):
        res = await process_hr_debrief_turn(
            interview_id="iv-alex-99",
            hr_question="Why did they get a high recommendation on database architecture?"
        )

        assert res["interview_id"] == "iv-alex-99"
        assert "response_text" in res
        assert len(res["response_text"]) > 0
        assert "audio_b64" in res
        assert "PgBouncer" in res["response_text"] or "vector" in res["response_text"] or "database" in res["response_text"].lower()


def test_debrief_api_endpoints():
    mock_session_data = [
        {
            "id": "db-999",
            "interview_id": "iv-alex-99",
            "candidate_id": "c-alex",
            "meet_link": "https://meet.google.com/mgr-test",
            "status": "Manager Agent Waiting",
            "summary": "Debrief session ready",
            "knowledge_context": {"candidate_id": "c-alex"}
        }
    ]

    with patch("app.services.database.db.query", new_callable=AsyncMock, return_value=mock_session_data):
        response = client.get("/api/debrief/iv-alex-99", headers={"X-User-Role": "hr"})
        assert response.status_code == 200
        data = response.json()
        assert data["interview_id"] == "iv-alex-99"
        assert "meet_link" in data
