"""Sourcing sub-agent: resume corpus -> parsed profiles -> database persistence -> embedded."""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from app.embeddings.embedder import get_embedder
from app.embeddings.store import upsert_embedding
from app.services.parser import parse_resume_bytes, extract_email_from_text, ResumeParseError, ParsedResume

logger = logging.getLogger("talentops.sourcing")


def parse_pdf(path: str) -> str:
    """Extract text from a PDF, DOCX, or text resume file."""
    try:
        if not path or not isinstance(path, str):
            raise ResumeParseError("Invalid path provided")
        with open(path, "rb") as f:
            content = f.read()
        parsed = parse_resume_bytes(content, file_name=path)
        return parsed.raw_text
    except ResumeParseError as e:
        logger.error("Failed to parse resume file %s: %s", path, e)
        raise
    except Exception as e:
        logger.error("Unexpected error parsing file %s: %s", path, e)
        raise ResumeParseError(f"Error parsing resume content at {path}: {e}") from e


def extract_profile(text: str, file_name: str | None = None) -> ParsedResume:
    """Structured profile extraction from resume raw text."""
    if not text or not isinstance(text, str) or not text.strip():
        raise ValueError(f"Resume text is empty or invalid for file {file_name}")

    fname = file_name or "resume.pdf"
    if not fname.endswith((".pdf", ".docx", ".txt", ".md")):
        fname = f"{fname}.pdf"

    return parse_resume_bytes(text.encode("utf-8"), file_name=fname)


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
                        loaded_temp.append({"id": fname.rsplit(".", 1)[0], "text": text, "email": email, "pdf_path": fpath})
                    except Exception as exc:
                        logger.error("Failed to load temp upload resume %s: %s", fname, exc)
        if loaded_temp:
            return loaded_temp

        logger.error("run_sourcing called with no candidate corpus. Supply resume files via corpus.")
        return []

    loaded = []
    for item in corpus:
        if "pdf_path" in item:
            try:
                text = parse_pdf(item["pdf_path"])
                email = extract_email_from_text(text)
                loaded.append({
                    "id": item.get("id") or f"cand_{uuid.uuid4().hex[:10]}",
                    "text": text,
                    "email": email,
                    "pdf_path": item["pdf_path"]
                })
            except Exception as exc:
                logger.error("Failed to load resume for candidate %s: %s", item.get("id"), exc)
        else:
            loaded.append(item)
    return loaded


async def run_sourcing_async(run_id: str, goal: str, corpus: list[dict] | None = None) -> dict[str, Any]:
    """Async candidate sourcing pipeline: parse -> database persistence (candidates & projects) -> embedding."""
    embedder = get_embedder()
    profiles: list[dict[str, Any]] = []

    from app.services.database import db

    for entry in _load_corpus(corpus):
        try:
            cand_id = entry.get("id") or f"cand_{uuid.uuid4().hex[:10]}"
            parsed = extract_profile(entry["text"], file_name=entry.get("pdf_path") or f"{cand_id}.pdf")

            cand_name = parsed.candidate_name or f"Candidate {cand_id[:6]}"
            cand_email = parsed.email or entry.get("email") or ""
            cand_phone = parsed.phone or ""
            cand_summary = parsed.summary or ""
            cand_skills = parsed.skills or []
            cand_projects = parsed.projects or []

            # --- AI Extraction & Eligibility Summary ---
            try:
                from app.services.llm_clients import openrouter_chat
                import json
                
                prompt = f"""
                You are an expert HR recruiter. Read the following candidate resume text and extract the candidate's full name, email address, and write a brief summary of the candidate.
                Most importantly, evaluate why this candidate is eligible or not eligible based on this goal: '{goal}'.
                
                Return ONLY a JSON object with these keys:
                - candidate_name: string (the candidate's full name)
                - email: string (the candidate's email address)
                - eligibility_summary: string (why they are eligible or not eligible)
                
                Resume Text:
                {entry.get("text", "")[:4000]}
                """
                llm_response = await openrouter_chat(
                    [{"role": "user", "content": prompt}],
                    json_mode=True,
                    max_tokens=600
                )
                llm_data = json.loads(llm_response)
                
                if llm_data.get("candidate_name") and llm_data["candidate_name"].strip():
                    cand_name = llm_data["candidate_name"].strip()
                if llm_data.get("email") and llm_data["email"].strip():
                    cand_email = llm_data["email"].strip()
                if llm_data.get("eligibility_summary") and llm_data["eligibility_summary"].strip():
                    cand_summary = llm_data["eligibility_summary"].strip()
            except Exception as llm_exc:
                logger.error("LLM extraction in sourcing failed: %s", llm_exc)

            # 1. Database persistence: Save candidate to candidates table
            candidate_payload = {
                "id": cand_id,
                "name": cand_name,
                "email": cand_email if cand_email else None,
                "phone": cand_phone,
                "summary": cand_summary,
                "skills": cand_skills,
                "experience": [e.model_dump() for e in parsed.experience] if parsed.experience else [],
                "education": [e.model_dump() for e in parsed.education] if parsed.education else [],
                "raw_text": entry.get("text", ""),
                "resume_path": entry.get("pdf_path", ""),
            }
            try:
                await db.insert("candidates", candidate_payload)
            except Exception as exc:
                logger.warning("Supabase candidate insert failed, attempting update for %s: %s", cand_id, exc)
                try:
                    await db.update("candidates", cand_id, candidate_payload)
                except Exception as update_exc:
                    logger.warning("Supabase candidate update failed for %s: %s", cand_id, update_exc)

            # 2. Database persistence: Save projects to projects table
            for proj in cand_projects:
                try:
                    await db.insert("projects", {
                        "candidate_id": cand_id,
                        "title": proj.title,
                        "description": proj.description,
                        "technologies": proj.technologies,
                        "url": proj.url,
                    })
                except Exception as exc:
                    logger.warning("Supabase project insert notice for candidate %s: %s", cand_id, exc)

            # 3. Embedding vector store
            text_for_embed = f"{cand_name} {cand_summary} {' '.join(cand_skills)}"
            vector = embedder.embed(text_for_embed)
            upsert_embedding(
                run_id,
                kind="candidate",
                ref_id=cand_id,
                vector=vector,
                metadata={
                    "name": cand_name,
                    "email": cand_email,
                    "skills": cand_skills,
                    "projects_count": len(cand_projects),
                },
            )

            profiles.append({
                "id": cand_id,
                "name": cand_name,
                "email": cand_email,
                "phone": cand_phone,
                "summary": cand_summary,
                "skills": cand_skills,
                "projects": [p.model_dump() for p in cand_projects],
            })
        except Exception as exc:
            logger.error("Error processing resume candidate '%s' during sourcing: %s", entry.get("id"), exc)
            continue

    return {"candidates": profiles, "count": len(profiles)}


def run_sourcing(run_id: str, goal: str, corpus: list[dict] | None = None) -> dict[str, Any]:
    """Sync wrapper for run_sourcing_async."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(run_sourcing_async(run_id, goal, corpus))
        else:
            return loop.run_until_complete(run_sourcing_async(run_id, goal, corpus))
    except Exception:
        return asyncio.run(run_sourcing_async(run_id, goal, corpus))
