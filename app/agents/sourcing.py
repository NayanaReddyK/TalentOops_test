"""Sourcing sub-agent: resume corpus -> parsed profiles -> enriched -> embedded."""
from __future__ import annotations

import logging
from typing import Any

from app.agents.scraper import get_scraper
from app.embeddings.embedder import get_embedder
from app.embeddings.store import upsert_embedding
from app.llm.client import get_llm_client

logger = logging.getLogger("talentops.sourcing")

# _MOCK_CORPUS removed — no silent mock fallback in production.
# Real candidate resume files must be supplied via the `corpus` parameter.


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
    """Load and validate candidate corpus from real resume files.

    Raises ValueError if no corpus is supplied — no mock fallback.
    """
    if not corpus:
        logger.error(
            "run_sourcing called with no candidate corpus. "
            "Supply resume files via the `corpus` parameter. "
            "No mock data will be injected."
        )
        return []
    loaded = []
    for item in corpus:
        if "pdf_path" in item:
            try:
                text = parse_pdf(item["pdf_path"])
                email = extract_email_from_text(text)
                loaded.append({"id": item["id"], "text": text, "email": email})
            except Exception as exc:
                logger.error("Failed to load resume for candidate %s: %s", item.get("id"), exc)
        else:
            loaded.append(item)
    if not loaded:
        logger.error(
            "Corpus supplied but no valid candidate resumes could be loaded. "
            "Check file paths and formats. No mock data will be injected."
        )
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
