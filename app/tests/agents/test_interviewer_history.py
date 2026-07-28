"""Tests for interviewer dynamic question generation preserving full session history across turns."""
import pytest
from unittest.mock import AsyncMock, patch
from app.agents.interviewer import generate_dynamic_question


@pytest.mark.asyncio
async def test_generate_dynamic_question_first_turn():
    """Verify Turn 1 (empty history) uses opening system prompt."""
    with patch("app.services.llm_clients.openrouter_chat", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Tell me about your Python background."
        with patch("app.config.settings.OPENROUTER_API_KEY", "mock-key"), patch("app.config.settings.LLM_PROVIDER", "openrouter"):
            question = await generate_dynamic_question(
                job_title="Senior Python Engineer",
                parsed_resume_text="5 years Python experience",
                job_description="Build distributed systems",
                last_candidate_answer="Hello, ready for the interview.",
                asked_questions_list=[],
                history=[],
            )

            assert question == "Tell me about your Python background."
            assert mock_llm.called
            messages = mock_llm.call_args[0][0]
            system_prompt = messages[0]["content"]
            assert "Turn 1 (Opening Question)" in system_prompt


@pytest.mark.asyncio
async def test_generate_dynamic_question_preserves_history_on_short_answer():
    """Verify Turn 4 with short answer 'agent handover' passes full 3-turn history to LLM and avoids cold-start text."""
    history = [
        {"question": "Tell me about your background.", "answer": "I built a multi-agent system using Python and LangChain."},
        {"question": "How did the agents communicate?", "answer": "They used Redis pub/sub for event routing."},
        {"question": "What happened during failover?", "answer": "We implemented a heartbeat monitor."},
    ]

    with patch("app.services.llm_clients.openrouter_chat", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "How did you ensure state consistency during the agent handover in your Redis architecture?"
        with patch("app.config.settings.OPENROUTER_API_KEY", "mock-key"), patch("app.config.settings.LLM_PROVIDER", "openrouter"):
            question = await generate_dynamic_question(
                job_title="Senior AI Engineer",
                parsed_resume_text="Experience with multi-agent systems and Redis",
                job_description="Design multi-agent orchestration",
                last_candidate_answer="agent handover",
                asked_questions_list=[h["question"] for h in history],
                history=history,
            )

            assert question == "How did you ensure state consistency during the agent handover in your Redis architecture?"
            assert "beginning of the interview" not in question.lower()

            messages = mock_llm.call_args[0][0]
            system_prompt = messages[0]["content"]
            assert "Turn 4" in system_prompt
            assert "Full Interview History So Far" in system_prompt
            assert "multi-agent system" in system_prompt
            assert "Redis pub/sub" in system_prompt
            assert "agent handover" in system_prompt
            assert "Do NOT claim or state that this is the beginning of the interview" in system_prompt


@pytest.mark.asyncio
async def test_generate_dynamic_question_fallback_uses_history():
    """Verify fallback when LLM fails or is offline uses history context instead of resetting memory."""
    history = [
        {"question": "Tell me about your tech stack.", "answer": "I used PostgreSQL and Celery for background jobs."},
    ]

    # Force LLM exception to test fallback
    with patch("app.services.llm_clients.openrouter_chat", side_effect=Exception("API Error")):
        with patch("app.config.settings.OPENROUTER_API_KEY", "mock-key"), patch("app.config.settings.LLM_PROVIDER", "openrouter"):
            question = await generate_dynamic_question(
                job_title="Backend Developer",
                parsed_resume_text="PostgreSQL & Celery",
                job_description="Maintain API",
                last_candidate_answer="agent handover",
                asked_questions_list=["Tell me about your tech stack."],
                history=history,
            )

            assert "beginning of the interview" not in question.lower()
            assert "agent handover" in question
            assert "PostgreSQL and Celery" in question
