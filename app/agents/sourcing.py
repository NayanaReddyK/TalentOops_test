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




def extract_profile(text: str, file_name: str | None = None) -> dict[str, Any]:
    """Structured profile extraction via the LLM client."""
    if not text or not isinstance(text, str) or not text.strip():
        raise ValueError(f"Resume text is empty or invalid for file {file_name}")

    from app.services.parser import extract_candidate_metadata, clean_candidate_name
    meta = extract_candidate_metadata(text, file_name=file_name)

    llm = get_llm_client()
    try:
        profile = llm.complete_json(
            system="Extract a candidate profile from the resume text.",
            user=text,
            schema_hint={"name": "str", "email": "str", "skills": "list[str]", "years_experience": "int", "summary": "str"},
        )
    except Exception:
        profile = {}

    extracted_name = profile.get("name") if isinstance(profile, dict) else ""
    if not extracted_name or extracted_name == "Candidate":
        extracted_name = meta.get("full_name") or clean_candidate_name(file_name)
    else:
        extracted_name = clean_candidate_name(extracted_name)

    profile["name"] = extracted_name
    profile["email"] = (profile.get("email") if isinstance(profile, dict) else None) or meta.get("email") or extract_email_from_text(text)
    return profile


def _load_corpus(corpus: list[dict] | None) -> list[dict]:
    """Load and validate candidate corpus from real resume files."""
    if not corpus:
        import os
        loaded_temp = []
        if os.path.exists("temp_uploads"):
            for fname in sorted(os.listdir("temp_uploads"), reverse=True):
                fpath = os.path.join("temp_uploads", fname)
                if os.path.isfile(fpath) and not fname.startswith("."):
                    try:
                        text = parse_pdf(fpath)
                        email = extract_email_from_text(text)
                        loaded_temp.append({"id": fname.rsplit(".", 1)[0], "text": text, "email": email})
                    except Exception as exc:
                        logger.error("Failed to load temp upload resume %s: %s", fname, exc)
        if loaded_temp:
            return loaded_temp

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
        try:
            profile = extract_profile(entry["text"], file_name=entry.get("id"))
            cand_name = profile.get("name") or "Candidate"
            cand_email = profile.get("email") or entry.get("email") or f"{entry['id']}@example.com"
            profile["name"] = cand_name
            profile["email"] = cand_email

            context = scraper.enrich(f"https://example.com/{entry['id']}", text_content=entry["text"])
            merged_skills = list({*(profile.get("skills") or []), *context.get("skills", [])})

            text_for_embed = f"{profile.get('summary', '')} {' '.join(merged_skills)}"

            vector = embedder.embed(text_for_embed)
            upsert_embedding(
                run_id,
                kind="candidate",
                ref_id=entry["id"],
                vector=vector,
                metadata={"profile": profile, "name": cand_name, "email": cand_email, "skills": merged_skills},
            )

            profiles.append({"id": entry["id"], "name": cand_name, "profile": profile, "email": cand_email, "skills": merged_skills})
        except Exception as exc:
            logger.error("Error processing resume candidate '%s' during sourcing: %s", entry.get("id"), exc)
            continue

    return {"candidates": profiles, "count": len(profiles)}
