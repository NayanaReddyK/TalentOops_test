"""Sourcing sub-agent: resume corpus -> parsed profiles -> enriched -> embedded."""
from __future__ import annotations

import logging
from typing import Any

from app.agents.scraper import get_scraper
from app.embeddings.embedder import get_embedder
from app.embeddings.store import upsert_embedding
from app.llm.client import get_llm_client

logger = logging.getLogger("talentops.sourcing")

_MOCK_CORPUS = [
    {"id": "cand-001", "text": "Priya Rao. Senior backend engineer. Python, PyTorch, asyncio, Postgres, Kafka. 8 years."},
    {"id": "cand-002", "text": "Sam Lee. Data scientist. Python, PyTorch, SQL, statistics. 5 years."},
    {"id": "cand-003", "text": "Alex Kim. Frontend engineer. React, TypeScript, CSS. 4 years."},
]


from app.services.parser import parse_resume, extract_email_from_text, ResumeParseError


def parse_pdf(path: str) -> str:
    """Extract text from a PDF, DOCX, or text resume file."""
    try:
        parsed = parse_resume(path)
        return parsed.raw_text
    except ResumeParseError as e:
        logger.error("Failed to parse resume file %s: %s", path, e)
        raise
    except Exception as e:
        logger.error("Unexpected error parsing file %s: %s", path, e)
        raise ResumeParseError(f"Error parsing resume content at {path}: {e}") from e



from app.services.gdrive_service import extract_email_from_text, fetch_resumes_from_drive


def extract_profile(text: str) -> dict[str, Any]:
    """Structured profile extraction via the LLM client."""
    llm = get_llm_client()
    profile = llm.complete_json(
        system="Extract a candidate profile from the resume text.",
        user=text,
        schema_hint={"name": "str", "email": "str", "skills": "list[str]", "years_experience": "int", "summary": "str"},
    )
    if not profile.get("email"):
        profile["email"] = extract_email_from_text(text)
    return profile


def _load_corpus(corpus: list[dict] | None) -> list[dict]:
    if not corpus:
        logger.info("No candidate resume file uploaded. Using default candidate corpus.")
        return _MOCK_CORPUS
    loaded = []
    for item in corpus:
        if "pdf_path" in item:
            text = parse_pdf(item["pdf_path"])
            email = extract_email_from_text(text)
            loaded.append({"id": item["id"], "text": text, "email": email})
        else:
            loaded.append(item)
    if not loaded:
        logger.warning("No valid candidate resume loaded from file. Using default candidate corpus.")
        return _MOCK_CORPUS
    return loaded


def run_sourcing(run_id: str, goal: str, corpus: list[dict] | None = None) -> dict[str, Any]:
    embedder = get_embedder()
    scraper = get_scraper()
    profiles: list[dict[str, Any]] = []

    for entry in _load_corpus(corpus):
        profile = extract_profile(entry["text"])
        context = scraper.enrich(f"https://example.com/{entry['id']}")
        merged_skills = list({*(profile.get("skills") or []), *context.get("skills", [])})

        text_for_embed = f"{profile.get('summary', '')} {' '.join(merged_skills)}"
        candidate_email = profile.get("email") or entry.get("email") or f"{entry['id']}@example.com"
        profile["email"] = candidate_email

        vector = embedder.embed(text_for_embed)
        upsert_embedding(
            run_id,
            kind="candidate",
            ref_id=entry["id"],
            vector=vector,
            metadata={"profile": profile, "email": candidate_email, "skills": merged_skills},
        )

        profiles.append({"id": entry["id"], "profile": profile, "email": candidate_email, "skills": merged_skills})

    return {"candidates": profiles, "count": len(profiles)}
