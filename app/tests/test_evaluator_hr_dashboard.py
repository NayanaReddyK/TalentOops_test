"""Tests for EvaluatorAgent enhancement and HR Evaluation API endpoint."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.evaluator_agent import EvaluatorAgent
from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_evaluator_agent_comprehensive_evaluation():
    agent = EvaluatorAgent(run_id="test-run")

    transcript_turns = [
        {"speaker": "interviewer", "text": "Can you explain how async Python works and how you manage event loops?"},
        {"speaker": "candidate", "text": "Async Python uses asyncio event loops to schedule coroutines non-blockingly. I designed high-throughput microservices using FastAPI and asyncio."},
        {"speaker": "interviewer", "text": "How do you handle SQL query optimization under heavy database load?"},
        {"speaker": "candidate", "text": "I optimize queries by adding HNSW vector indexes, composite B-tree indexes, and connection pooling using PgBouncer to prevent database locks."}
    ]

    rubric = {
        "competencies": [
            {"competency_id": "async_python", "keywords": ["asyncio", "coroutine", "event loop", "fastapi"]},
            {"competency_id": "database_optimization", "keywords": ["index", "pgbouncer", "vector", "sql"]}
        ]
    }

    mock_db_return = {"id": "sc-12345"}
    with patch("app.agents.evaluator_agent.db.insert", new_callable=AsyncMock, return_value=mock_db_return), \
         patch("app.agents.evaluator_agent.upsert_embedding"):

        result = await agent.evaluate_transcript(
            interview_id="iv-test-99",
            candidate_id="c-alex",
            rubric=rubric,
            transcript_turns=transcript_turns
        )

        assert result["interview_id"] == "iv-test-99"
        assert result["candidate_id"] == "c-alex"
        assert "scorecard" in result
        assert "behavioral_metrics" in result
        assert "detailed_competencies" in result
        assert "full_transcript_evaluations" in result
        assert "final_recommendation" in result

        # Check behavioral metrics structure
        bm = result["behavioral_metrics"]
        assert "confidence_level" in bm
        assert "communication_clarity" in bm
        assert "response_structure" in bm
        assert "candidate_engagement" in bm
        assert 0.0 <= bm["confidence_level"] <= 1.0

        # Check final recommendation
        rec = result["final_recommendation"]
        assert rec["hiring_recommendation"] in ["Strong Hire", "Hire", "Hold", "Reject"]
        assert 0.0 <= rec["overall_suitability_score"] <= 100.0
        assert len(rec["executive_summary"]) > 0

        # Check turn evaluations
        turns_eval = result["full_transcript_evaluations"]
        assert len(turns_eval) == 2  # 2 Q&A pairs
        assert "question" in turns_eval[0]
        assert "candidate_answer" in turns_eval[0]
        assert "technical_accuracy" in turns_eval[0]


def test_get_interview_evaluation_endpoint_unauthorized():
    # Without HR role header
    response = client.get("/api/interviews/iv-alex/evaluation")
    assert response.status_code == 403


def test_get_interview_evaluation_endpoint_authorized():
    mock_scorecard_data = [
        {
            "id": "sc-999",
            "interview_id": "iv-alex",
            "candidate_id": "c-alex",
            "scorecard": {"overall_fit": 0.88, "needs_human_review": False},
            "behavioral_metrics": {
                "confidence_level": 0.92,
                "communication_clarity": 0.88,
                "response_structure": 0.85,
                "candidate_engagement": 0.95
            },
            "detailed_competencies": [
                {
                    "competency_id": "async_python",
                    "score": 0.90,
                    "technical_accuracy": 92.0,
                    "strengths": ["Clear understanding of event loops"],
                    "areas_for_improvement": ["Could mention uvloop"]
                }
            ],
            "full_transcript_evaluations": [
                {
                    "question_number": 1,
                    "question": "Explain async Python?",
                    "candidate_answer": "Async Python uses asyncio.",
                    "confidence_score": 0.9,
                    "evaluator_notes": "Strong technical accuracy."
                }
            ],
            "final_recommendation": {
                "overall_suitability_score": 88.0,
                "hiring_recommendation": "Strong Hire",
                "executive_summary": "Excellent technical candidate with deep Python expertise."
            },
            "created_at": "2026-07-27T10:00:00Z"
        }
    ]

    with patch("app.services.database.db.query", new_callable=AsyncMock, return_value=mock_scorecard_data):
        response = client.get(
            "/api/interviews/iv-alex/evaluation",
            headers={"X-User-Role": "hr"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["interview_id"] == "iv-alex"
        assert data["final_recommendation"]["hiring_recommendation"] == "Strong Hire"
        assert data["behavioral_metrics"]["confidence_level"] == 0.92
