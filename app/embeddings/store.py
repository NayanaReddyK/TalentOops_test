"""Vector persistence for embedding pipeline."""
from __future__ import annotations

import logging
from typing import Any

from app.embeddings.embedder import cosine
from app.supabase_client import _get_client

logger = logging.getLogger("talentops.embeddings.store")


def upsert_embedding(run_id: str, kind: str, ref_id: str, vector: list[float], metadata: dict) -> None:
    client = _get_client()
    if client is None:
        raise ValueError("Supabase is not configured. Enforcing REAL API execution.")
        
    row = {"run_id": run_id, "kind": kind, "ref_id": ref_id, "embedding": vector, "metadata": metadata}
    try:
        client.table("embeddings").upsert(row, on_conflict="run_id,kind,ref_id").execute()
    except Exception as exc:
        try:
            client.table("embeddings").insert(row).execute()
        except Exception as insert_exc:
            logger.error("Remote 'embeddings' table insert failed (%s)", type(insert_exc).__name__)
            raise


def match(run_id: str, query_vector: list[float], kind: str, top_k: int) -> list[dict]:
    client = _get_client()
    if client is None:
        raise ValueError("Supabase is not configured. Enforcing REAL API execution.")

    try:
        resp = client.rpc(
            "match_embeddings",
            {"p_run_id": run_id, "p_kind": kind, "p_query": query_vector, "p_top_k": top_k},
        ).execute()
        return resp.data or []
    except Exception as exc:
        logger.error("Supabase match_embeddings RPC failed: %s", exc)
        raise
