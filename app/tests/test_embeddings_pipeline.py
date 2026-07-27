"""Tests for embedding generation pipeline (dimensions, retries, batching)."""
import pytest
from unittest.mock import MagicMock, patch
from app.config import get_settings
from app.embeddings.embedder import (
    RemoteEmbedder,
    get_embedder,
    retry_with_backoff,
)


class MockEmbedder:
    def __init__(self, dim: int):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        return [0.1] * self.dim

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * self.dim for _ in texts]


def test_mock_embedder_dimension():
    settings = get_settings()
    embedder = MockEmbedder(dim=settings.embed_dim)
    vec = embedder.embed("Senior Python Developer with FastAPI and Postgres")
    assert len(vec) == settings.embed_dim
    assert isinstance(vec[0], float)


def test_remote_embedder_dimension_param():
    with patch("openai.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.data = [MagicMock(embedding=[0.1] * 384)]
        mock_client.embeddings.create.return_value = mock_resp

        embedder = RemoteEmbedder(provider="openrouter")
        vec = embedder.embed("Candidate profile summary text")

        assert len(vec) == 384
        mock_client.embeddings.create.assert_called_once()
        _, kwargs = mock_client.embeddings.create.call_args
        assert kwargs.get("dimensions") == 384 or kwargs.get("model") == "text-embedding-3-small"


def test_retry_with_backoff_decorator():
    call_count = 0

    @retry_with_backoff(max_retries=3, initial_delay=0.01)
    def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("API Rate Limit 429 Too Many Requests")
        return [0.5] * 384

    result = flaky_function()
    assert result == [0.5] * 384
    assert call_count == 3


def test_retry_with_backoff_fails_after_max_retries():
    @retry_with_backoff(max_retries=2, initial_delay=0.01)
    def failing_function():
        raise RuntimeError("API Server Error 500")

    with pytest.raises(RuntimeError, match="API Server Error 500"):
        failing_function()


def test_embed_batch():
    embedder = MockEmbedder(dim=384)
    texts = ["Python engineer", "React frontend lead", "DevOps SRE"]
    if hasattr(embedder, "embed_batch"):
        vectors = embedder.embed_batch(texts)
    else:
        vectors = [embedder.embed(t) for t in texts]

    assert len(vectors) == 3
    for v in vectors:
        assert len(v) == 384
