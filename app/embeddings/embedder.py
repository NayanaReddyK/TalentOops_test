"""Embedding generation for JD / candidate vector matching."""
from __future__ import annotations

import hashlib
import math
from typing import Protocol

from app.config import get_settings


class Embedder(Protocol):
    dim: int

    def embed(self, text: str) -> list[float]:
        ...


class MockEmbedder:
    """Deterministic hashing embedder."""

    def __init__(self, dim: int):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = (text or "").lower().split()
        for tok in tokens:
            h = int(hashlib.sha256(tok.encode()).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class RemoteEmbedder:
    """OpenAI-compatible embeddings endpoint (lazy)."""

    def __init__(self, provider: str):
        settings = get_settings()
        from openai import OpenAI

        if provider == "openrouter":
            self._client = OpenAI(api_key=settings.OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
        elif provider == "groq":
            self._client = OpenAI(api_key=settings.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
        else:
            raise ValueError(f"Unknown embed provider: {provider}")
        self.dim = settings.embed_dim
        self._model = "text-embedding-3-small"

    def embed(self, text: str) -> list[float]:
        resp = self._client.embeddings.create(model=self._model, input=text)
        return resp.data[0].embedding


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def get_embedder() -> Embedder:
    settings = get_settings()
    if settings.embed_provider == "mock":
        return MockEmbedder(settings.embed_dim)
    return RemoteEmbedder(settings.embed_provider)
