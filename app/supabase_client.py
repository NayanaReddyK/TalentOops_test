"""Supabase-backed event logging.

The supabase-py client is synchronous, so all writes are pushed off the event
loop with ``asyncio.to_thread`` and fired as background ``asyncio`` tasks — the
supervisor graph never blocks on a DB round-trip. If Supabase is not configured
we fall back to structured stdout logging so the graph still boots and is
testable with zero credentials.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings

logger = logging.getLogger("talentops.events")

_client = None
_pending: set[asyncio.Task] = set()


def _get_client():
    """Lazily construct the Supabase client (singleton)."""
    global _client
    if _client is not None:
        return _client
    settings = get_settings()
    if not settings.supabase_configured:
        return None
    from supabase import create_client

    _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


def _insert_sync(row: dict[str, Any]) -> None:
    client = _get_client()
    if client is None:
        logger.info("[event:stdout] %s", row)
        return
    try:
        client.table("events").insert(row).execute()
    except Exception as exc:
        logger.warning("[event:db_fallback] Failed writing event to Supabase: %s", exc)


async def _write(row: dict[str, Any]) -> None:
    try:
        await asyncio.to_thread(_insert_sync, row)
    except Exception:
        logger.exception("Failed to write event: %s", row.get("event_type"))


def log_event(
    run_id: str,
    source: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Fire-and-forget: schedule an event write as a background asyncio task."""
    row = {
        "run_id": run_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "event_type": event_type,
        "payload": payload or {},
    }
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        _insert_sync(row)
        return

    task = loop.create_task(_write(row))
    _pending.add(task)
    task.add_done_callback(_pending.discard)


async def flush_events() -> None:
    """Await all in-flight event writes (call on shutdown / after a run)."""
    if _pending:
        await asyncio.gather(*list(_pending), return_exceptions=True)
