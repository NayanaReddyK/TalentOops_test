"""Unit & integration tests verifying Interviewer & Consent Agent upgrades."""
import pytest
from app.agents.consent_agent import parse_consent_intent_detailed, parse_consent_intent
from app.agents.interviewer_fsm import InterviewerFSM, InterviewState
from app.agents.interviewer import is_semantic_duplicate, generate_dynamic_question


def test_consent_agent_regex_word_boundary():
    """Verify regex word-boundary matching prevents false positives like 'nowhere' or 'booking'."""
    # Words containing substring 'no' or 'ok' but not as standalone words
    res1 = parse_consent_intent_detailed("I live in nowhere near the city")
    assert res1.consent_granted is False
    assert res1.confidence_score == 0.0
    assert "Ambiguous or hesitant" in res1.reasoning

    res2 = parse_consent_intent_detailed("I am booking a hotel for Loki")
    assert res2.consent_granted is False
    assert res2.confidence_score == 0.0

    # Explicit standalone affirmative consent
    res3 = parse_consent_intent_detailed("Yes, I explicitly agree to the recording.")
    assert res3.consent_granted is True
    assert res3.confidence_score == 0.95

    # Explicit standalone negative refusal
    res4 = parse_consent_intent_detailed("No, I decline to be recorded.")
    assert res4.consent_granted is False
    assert res4.confidence_score == 0.95


def test_consent_agent_default_deny_on_ambiguity():
    """Verify hesitant or ambiguous inputs ('I'm not sure') return consent_granted=False."""
    hesitant_inputs = [
        "I'm not sure about this",
        "Let me think about it",
        "What happens to the video later?",
        "Maybe later",
    ]
    for inp in hesitant_inputs:
        result = parse_consent_intent_detailed(inp)
        assert result.consent_granted is False, f"Failed for input: {inp}"
        assert parse_consent_intent(inp) is False


@pytest.mark.asyncio
async def test_interviewer_fsm_turn_distribution_and_embedding_coverage():
    """Verify even turn distribution across states and embedding-based coverage."""
    rubric = {
        "competencies": [
            {"competency_id": "python_asyncio", "keywords": ["asyncio", "coroutine", "event loop"], "description": "Asynchronous Python programming with asyncio"},
            {"competency_id": "postgres_indexing", "keywords": ["postgres", "btree", "indexing"], "description": "PostgreSQL database indexing and query optimization"},
        ]
    }
    brief = {
        "competencies_to_probe": [
            {"competency_id": "python_asyncio"},
            {"competency_id": "postgres_indexing"},
        ]
    }

    class DummySession:
        async def inject_context(self, text: str) -> None:
            pass

        async def next_turn(self, candidate_text: str) -> str:
            return f"Follow up question to '{candidate_text}'"

    fsm = InterviewerFSM(rubric=rubric, brief=brief, session=DummySession())

    # Candidate turns
    turns = [
        "I have 5 years of backend engineering experience.",
        "I built high-throughput microservices using Python asyncio coroutines and event loops.",
        "For database storage, I optimized complex queries on PostgreSQL using BTree indexing.",
        "I also designed distributed microservice architectures.",
    ]

    res = await fsm.run_interview(turns, transcript_ref="ref-123")

    # Verify all 4 states (OPENING, BACKGROUND, PROBING, FOLLOWUPS) received 1 turn each
    assert len(fsm._questions) == 4
    # Verify embedding/keyword coverage
    assert fsm._covered(rubric["competencies"][0]) is True
    assert fsm._covered(rubric["competencies"][1]) is True
    assert fsm._confidence(rubric["competencies"][0]) > 0.5


def test_semantic_duplicate_question_rejection():
    """Verify exact and semantic near-duplicates are correctly identified."""
    asked = [
        "Could you explain how Python asyncio manages event loops and concurrency?",
        "Walk me through your database indexing strategies in PostgreSQL.",
    ]

    # Exact duplicate
    assert is_semantic_duplicate("Could you explain how Python asyncio manages event loops and concurrency?", asked) is True

    # Semantic near-duplicate
    assert is_semantic_duplicate("How does the Python asyncio event loop handle concurrency?", asked) is True

    # Completely new question
    assert is_semantic_duplicate("Can you describe your experience with Docker container orchestration?", asked) is False


@pytest.mark.asyncio
async def test_generate_dynamic_question_with_fsm_context():
    """Verify generate_dynamic_question accepts uncovered competencies and state context."""
    q = await generate_dynamic_question(
        job_title="Senior Python Backend Engineer",
        parsed_resume_text="Experienced in FastAPI, SQL, and Docker.",
        job_description="Looking for Python backend expert.",
        last_candidate_answer="I mostly worked on simple REST APIs.",
        asked_questions_list=["Tell me about your background."],
        history=[{"question": "Tell me about your background.", "answer": "I mostly worked on simple REST APIs."}],
        uncovered_competencies=["postgres_indexing", "distributed_tracing"],
        current_state="PROBING",
    )

    assert len(q) > 10
    assert q != "Tell me about your background."
