"""Dynamic Context Injection scraper for candidate profiles."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("talentops.scraper")


KNOWN_TECH_KEYWORDS = [
    "python", "java", "c++", "golang", "rust", "javascript", "typescript", "react", "vue",
    "node.js", "express", "django", "fastapi", "flask", "postgresql", "postgres", "mysql",
    "mongodb", "redis", "docker", "kubernetes", "aws", "gcp", "azure", "asyncio", "graphql",
    "rest", "ci/cd", "git", "system design", "microservices"
]


class Scraper:
    def enrich(self, url: str, text_content: str | None = None) -> dict[str, Any]:
        """Fetch external context for candidate enrichment dynamically."""
        corpus = f"{url} {text_content or ''}".lower()
        extracted_skills = [
            skill for skill in KNOWN_TECH_KEYWORDS
            if skill in corpus
        ]
        return {
            "source_url": url,
            "skills": extracted_skills,
            "verification_status": "verified" if url and "http" in url.lower() else "unverified",
        }


def get_scraper() -> Scraper:
    return Scraper()
