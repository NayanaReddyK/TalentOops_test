"""Vector persistence for embedding pipeline."""
from __future__ import annotations

import logging
from typing import Any

from app.embeddings.embedder import cosine
from app.supabase_client import _get_client

logger = logging.getLogger("talentops.embeddings.store")

_MEM: list[dict[str, Any]] = []


def _upsert_mem(row: dict[str, Any]) -> None:
    """Helper to upsert a record into in-memory store cleanly."""
    for idx, item in enumerate(_MEM):
        if (
            item.get("run_id") == row.get("run_id")
            and item.get("kind") == row.get("kind")
            and item.get("ref_id") == row.get("ref_id")
        ):
            _MEM[idx] = row
            return
    _MEM.append(row)


def upsert_embedding(run_id: str, kind: str, ref_id: str, vector: list[float], metadata: dict) -> None:
    client = _get_client()
    row = {"run_id": run_id, "kind": kind, "ref_id": ref_id, "embedding": vector, "metadata": metadata}
    if client is None:
        _upsert_mem(row)
        return
    try:
        client.table("embeddings").upsert(row, on_conflict="run_id,kind,ref_id").execute()
    except Exception as exc:
        try:
            client.table("embeddings").insert(row).execute()
        except Exception as insert_exc:
            logger.info("Remote 'embeddings' table unavailable (%s); stored in memory fallback", type(insert_exc).__name__)
            _upsert_mem(row)


def match(run_id: str, query_vector: list[float], kind: str, top_k: int) -> list[dict]:
    client = _get_client()
    if client is None:
        scored = [
            {**r, "score": cosine(query_vector, r["embedding"])}
            for r in _MEM
            if r["run_id"] == run_id and r["kind"] == kind
        ]
        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:top_k]

    try:
        resp = client.rpc(
            "match_embeddings",
            {"p_run_id": run_id, "p_kind": kind, "p_query": query_vector, "p_top_k": top_k},
        ).execute()
        return resp.data or []
    except Exception as exc:
        logger.warning("Supabase match_embeddings RPC failed (%s); falling back to in-memory store: %s", type(exc).__name__, exc)
        scored = [
            {**r, "score": cosine(query_vector, r["embedding"])}
            for r in _MEM
            if r["run_id"] == run_id and r["kind"] == kind
        ]
        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:top_k]
