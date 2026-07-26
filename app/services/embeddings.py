"""Deterministic 64-dim embeddings + frozen enriched-JD store (Task 6.3)."""
import hashlib
import json
import math

from app.services.database import db

DIM = 64


def embed_text(text: str) -> list[float]:
    vec = [0.0] * DIM
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode()).digest()
        idx = digest[0] % DIM
        vec[idx] += (digest[1] / 255.0) - 0.5
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


async def store_enriched_jd(role_id: str, jd: str, appendix: dict) -> dict:
    if await db.query("enriched_jd", role_id=role_id):
        raise RuntimeError("enriched JD frozen")  # frozen alongside the rubric (D14)
    enriched = jd + "\n\n[HIDDEN CONTEXT APPENDIX]\n" + json.dumps(appendix, sort_keys=True)
    return await db.insert("enriched_jd", {
        "role_id": role_id, "enriched_jd": enriched,
        "embedding": embed_text(enriched), "frozen": True})
