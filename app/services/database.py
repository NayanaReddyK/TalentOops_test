"""Async data layer: thin supabase-py delegation with seamless in-memory fallback for missing remote tables."""
from __future__ import annotations

import uuid
import logging
from typing import Any
from app.config import settings
from app.services.logging import get_logger, get_request_id

logger = None
metrics_collector = None


class TranscriptFinalizedError(Exception):
    """Raised on transcript append after finalize (immutability guarantee)."""


class Database:
    def __init__(self) -> None:
        self._finalized: set[str] = set()
        self._memory_store: dict[str, list[dict[str, Any]]] = {}
        global logger, metrics_collector
        if logger is None:
            from app.services.logging import get_metrics
            logger = get_logger(__name__)
            metrics_collector = get_metrics()

    def _insert_mem(self, table: str, row: dict) -> dict:
        """Insert row into in-memory fallback store."""
        row_copy = dict(row)
        if "id" not in row_copy:
            row_copy["id"] = f"{table}-{uuid.uuid4().hex[:8]}"
        if table not in self._memory_store:
            self._memory_store[table] = []
        self._memory_store[table].append(row_copy)
        return row_copy

    async def insert(self, table: str, row: dict) -> dict:
        """Insert a row into the database with fallback to in-memory store if remote table is missing."""
        try:
            data = self._sb().table(table).insert(row).execute().data
            result = data[0] if data else row
            return result
        except Exception as e:
            if logger:
                logger.info(
                    "Remote table '%s' insert fallback to in-memory store (%s: %s)",
                    table, type(e).__name__, str(e).splitlines()[0] if str(e) else ""
                )
            if metrics_collector:
                metrics_collector.increment_error_count("database", "insert")
            return self._insert_mem(table, row)

    async def update(self, table: str, row_id: str, patch: dict) -> dict | None:
        """Update a row in the database with fallback to in-memory store."""
        try:
            data = self._sb().table(table).update(patch).eq("id", row_id).execute().data
            result = data[0] if data else None
            if result:
                return result
        except Exception as e:
            if logger:
                logger.info(
                    "Remote table '%s' update fallback to in-memory store (%s)",
                    table, type(e).__name__
                )
            if metrics_collector:
                metrics_collector.increment_error_count("database", "update")

        # Fallback to in-memory store
        items = self._memory_store.get(table, [])
        for item in items:
            if item.get("id") == row_id:
                item.update(patch)
                return item
        return None

    async def get(self, table: str, row_id: str) -> dict | None:
        """Fetch a row from database or in-memory fallback store."""
        try:
            data = self._sb().table(table).select("*").eq("id", row_id).execute().data
            if data:
                return data[0]
        except Exception:
            pass

        items = self._memory_store.get(table, [])
        for item in items:
            if item.get("id") == row_id:
                return item
        return None

    async def query(self, table: str, **eq: Any) -> list[dict]:
        """Query rows from database or in-memory fallback store."""
        try:
            q = self._sb().table(table).select("*")
            for k, v in eq.items():
                q = q.eq(k, v)
            data = q.execute().data
            if data is not None:
                return data
        except Exception:
            pass

        items = self._memory_store.get(table, [])
        results = []
        for item in items:
            match = True
            for k, v in eq.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                results.append(item)
        return results

    async def append_transcript(self, interview_id: str, chunk: dict) -> None:
        if interview_id in self._finalized:
            raise TranscriptFinalizedError(interview_id)

        row = await self.get("interviews", interview_id)
        if row:
            t_list = row.get("transcript") or []
            t_list.append(dict(chunk))
            await self.update("interviews", interview_id, {"transcript": t_list})

    async def finalize_transcript(self, interview_id: str) -> None:
        self._finalized.add(interview_id)

    async def get_transcript_chunks(self, interview_id: str) -> list[dict]:
        row = await self.get("interviews", interview_id)
        if row:
            return row.get("transcript") or []
        return []

    async def get_transcript_text(self, interview_id: str) -> str:
        chunks = await self.get_transcript_chunks(interview_id)
        return "\n".join(f"{c.get('speaker', '?')}: {c.get('text', '')}" for c in chunks)

    def _sb(self):
        from supabase import create_client
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


db = Database()
