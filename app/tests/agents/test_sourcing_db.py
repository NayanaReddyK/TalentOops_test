"""Unit tests for sourcing agent database persistence."""
import pytest
from unittest.mock import AsyncMock, patch
from app.agents.sourcing import run_sourcing_async

SAMPLE_RESUME = """
Alice Johnson
Fullstack Engineer
Email: alice@company.org

SUMMARY
Fullstack engineer with React and Python experience.

PROJECTS
- AI Talent Platform: Built using FastAPI, PostgreSQL, and React.
"""


@pytest.mark.asyncio
async def test_sourcing_database_persistence():
    inserted_records = {"candidates": [], "projects": []}

    async def mock_insert(table, row):
        if table in inserted_records:
            inserted_records[table].append(row)
        return row

    corpus = [{"id": "cand_alice", "text": SAMPLE_RESUME}]

    with patch("app.services.database.db.insert", side_effect=mock_insert), \
         patch("app.agents.sourcing.get_embedder") as mock_embedder:
        mock_embedder.return_value.embed.return_value = [0.1] * 384
        with patch("app.agents.sourcing.upsert_embedding"):
            result = await run_sourcing_async("run-test-1", "Hire Fullstack Dev", corpus)

    assert result["count"] == 1
    assert len(inserted_records["candidates"]) == 1
    assert inserted_records["candidates"][0]["name"] == "Alice Johnson"
    assert inserted_records["candidates"][0]["email"] == "alice@company.org"

    assert len(inserted_records["projects"]) >= 1
    assert any("AI Talent Platform" in p["title"] for p in inserted_records["projects"])
