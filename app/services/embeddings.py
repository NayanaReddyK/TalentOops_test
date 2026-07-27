"""Embeddings service adapter using the unified embedder."""
from __future__ import annotations

import json
from app.embeddings.embedder import get_embedder, cosine
from app.services.database import db


def embed_text(text: str) -> list[float]:
    """Generate vector embedding using the global embedder provider."""
    return get_embedder().embed(text)


async def store_enriched_jd(role_id: str, jd: str, appendix: dict) -> dict:
    if await db.query("enriched_jd", role_id=role_id):
        raise RuntimeError("enriched JD frozen")  # frozen alongside the rubric (D14)
    enriched = jd + "\n\n[HIDDEN CONTEXT APPENDIX]\n" + json.dumps(appendix, sort_keys=True)
    return await db.insert("enriched_jd", {
        "role_id": role_id,
        "enriched_jd": enriched,
        "embedding": embed_text(enriched),
        "frozen": True,
    })
