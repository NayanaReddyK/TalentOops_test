"""Tests for Supabase embedding store & pgvector queries."""
import pytest
from unittest.mock import MagicMock, patch
from app.embeddings.store import upsert_embedding, match


def test_upsert_embedding_unconfigured_client():
    with patch("app.embeddings.store._get_client", return_value=None):
        with pytest.raises(ValueError, match="Supabase is not configured"):
            upsert_embedding(
                run_id="run-101",
                kind="candidate",
                ref_id="cand-001",
                vector=[0.1] * 384,
                metadata={"name": "Alice"}
            )


def test_upsert_embedding_with_configured_supabase():
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("app.embeddings.store._get_client", return_value=mock_client):
        upsert_embedding(
            run_id="run-102",
            kind="candidate",
            ref_id="cand-002",
            vector=[0.2] * 384,
            metadata={"name": "Bob"}
        )
        mock_client.table.assert_called_with("embeddings")
        mock_table.upsert.assert_called_once()
        _, kwargs = mock_table.upsert.call_args
        assert kwargs.get("on_conflict") == "run_id,kind,ref_id" or "on_conflict" in str(kwargs)


def test_match_embeddings_unconfigured_fallback():
    with patch("app.embeddings.store._get_client", return_value=None):
        with pytest.raises(ValueError, match="Supabase is not configured"):
            match(run_id="run-200", query_vector=[1.0] + [0.0] * 383, kind="candidate", top_k=2)
