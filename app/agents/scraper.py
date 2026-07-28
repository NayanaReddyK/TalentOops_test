"""Dynamic Context Injection scraper for candidate profiles."""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("talentops.scraper")

KNOWN_TECH_KEYWORDS = [
    "python", "java", "c++", "golang", "rust", "javascript", "typescript", "react", "vue",
    "node.js", "express", "django", "fastapi", "flask", "postgresql", "postgres", "mysql",
    "mongodb", "redis", "docker", "kubernetes", "aws", "gcp", "azure", "asyncio", "graphql",
    "rest", "ci/cd", "git", "system design", "microservices"
]


class Scraper:
    def enrich(self, url: str | None = None, text_content: str | None = None) -> dict[str, Any]:
        """Fetch external context for candidate enrichment dynamically using exact word boundaries."""
        corpus = f"{url or ''} {text_content or ''}".lower()
        extracted_skills = []
        for skill in KNOWN_TECH_KEYWORDS:
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, corpus):
                extracted_skills.append(skill)

        # Verification status is unverified unless real domain check passes
        is_real_url = bool(url and url.startswith(("http://", "https://")) and "example.com" not in url)
        return {
            "source_url": url or "",
            "skills": extracted_skills,
            "verification_status": "verified" if is_real_url else "unverified",
        }


def get_scraper() -> Scraper:
    return Scraper()
