"""TDD unit tests for Phase 4 Candidate Evaluation & Demographic Fairness Guard."""
import pytest
from app.agents.scorecard_agent import ScorecardAgent, MIN_QUOTE_LEN
from app.services.fairness import calculate_k_anonymity
from app.graph.nodes import reporting_node


def test_quote_length_validation():
    agent = ScorecardAgent()
    transcript = "The candidate demonstrated extensive experience using Kafka and Redis to build real-time event streaming pipelines with high throughput."
    
    # Valid quote >= 40 chars
    long_quote = "extensive experience using Kafka and Redis to build real-time event streaming pipelines"
    val = agent._validate(transcript, {"quote": long_quote})
    assert val is not None
    assert val["validated"] is True
    
    # Invalid quote < 40 chars
    short_quote = "Kafka and Redis"
    val_short = agent._validate(transcript, {"quote": short_quote})
    assert val_short is None


def test_k_anonymity_suppression():
    cohort_data = {
        ("gender", "female"): [0.8, 0.85, 0.9, 0.82, 0.88],  # count 5 >= k=5
        ("gender", "nonbinary"): [0.9, 0.95],  # count 2 < k=5 (MUST be suppressed)
    }
    res = calculate_k_anonymity(cohort_data, k=5)
    
    female_cell = next(c for c in res["cells"] if c["value"] == "female")
    assert female_cell["suppressed"] is False
    assert female_cell["n"] == 5
    
    nonbinary_cell = next(c for c in res["cells"] if c["value"] == "nonbinary")
    assert nonbinary_cell["suppressed"] is True
    assert nonbinary_cell["n"] is None

from unittest.mock import patch, AsyncMock, MagicMock

@pytest.mark.asyncio
@patch("app.supabase_client._insert_sync")
@patch("app.services.database.db.insert", new_callable=AsyncMock)
@patch("app.agents.communication.get_email_client")
@patch("app.embeddings.embedder.RemoteEmbedder.embed", return_value=[0.1] * 384)
@patch("app.embeddings.embedder.RemoteEmbedder.embed_batch", return_value=[[0.1] * 384])
async def test_reporting_node_emits_stage_and_envelope(mock_embed_batch, mock_embed, mock_get_email_client, mock_insert, mock_log_event):
    mock_email_client = MagicMock()
    mock_email_client.send.return_value = MagicMock(message_id="mock_msg_id")
    mock_get_email_client.return_value = mock_email_client
    state = {
        "run_id": "run-301",
        "goal": "Build microservices",
        "top_candidate": "Priya Rao",
        "shortlist": [{"ref_id": "Alex Chen"}],
        "results": {"interview": {"needs_review": False}},
        "completed": ["interviewer"],
        "messages": [],
    }
    result_state = await reporting_node(state)
    assert result_state["stage"] == "HR_DEBRIEF"
    assert "reporting" in result_state["completed"]
    assert len(result_state["messages"]) == 1
    env = result_state["messages"][0]
    assert env["sender"] == "reporting"
    assert env["recipient"] == "manager"
    assert env["body"]["decision"] == "ADVANCE"
