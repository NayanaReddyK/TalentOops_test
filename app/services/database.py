"""Async data layer: thin supabase-py delegation."""
import uuid
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
        # Lazy initialization to avoid circular imports
        global logger, metrics_collector
        if logger is None:
            from app.services.logging import get_metrics
            logger = get_logger(__name__)
            metrics_collector = get_metrics()

    async def insert(self, table: str, row: dict) -> dict:
        """Insert a row into the database."""
        try:
            logger.info(
                "Attempting database insert",
                extra={
                    "table": table,
                    "row_keys": list(row.keys()),
                    "request_id": get_request_id()
                }
            )

            data = self._sb().table(table).insert(row).execute().data
            result = data[0] if data else {}

            logger.info(
                "Database insert successful",
                extra={
                    "table": table,
                    "row_id": result.get("id"),
                    "request_id": get_request_id()
                }
            )

            return result
        except Exception as e:
            logger.error(
                "Database insert failed",
                exc_info=True,
                extra={
                    "table": table,
                    "error_type": type(e).__name__,
                    "request_id": get_request_id()
                }
            )
            metrics_collector.increment_error_count("database", "insert")
            return {}

    async def update(self, table: str, row_id: str, patch: dict) -> dict | None:
        """Update a row in the database."""
        try:
            logger.info(
                "Attempting database update",
                extra={
                    "table": table,
                    "row_id": row_id,
                    "patch_keys": list(patch.keys()),
                    "request_id": get_request_id()
                }
            )

            data = self._sb().table(table).update(patch).eq("id", row_id).execute().data
            result = data[0] if data else None

            logger.info(
                "Database update successful",
                extra={
                    "table": table,
                    "row_id": row_id,
                    "request_id": get_request_id()
                }
            )

            return result
        except Exception as e:
            logger.error(
                "Database update failed",
                exc_info=True,
                extra={
                    "table": table,
                    "row_id": row_id,
                    "error_type": type(e).__name__,
                    "request_id": get_request_id()
                }
            )
            metrics_collector.increment_error_count("database", "update")
            return None

    async def get(self, table: str, row_id: str) -> dict | None:
        try:
            data = self._sb().table(table).select("*").eq("id", row_id).execute().data
            return data[0] if data else None
        except Exception as e:
            if logger:
                logger.error(
                    "Database get failed",
                    exc_info=True,
                    extra={
                        "table": table,
                        "row_id": row_id,
                        "error_type": type(e).__name__,
                        "request_id": get_request_id()
                    }
                )
            if metrics_collector:
                metrics_collector.increment_error_count("database", "get")
            return None

    async def query(self, table: str, **eq: Any) -> list[dict]:
        q = self._sb().table(table).select("*")
        for k, v in eq.items():
            q = q.eq(k, v)
        return q.execute().data

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
