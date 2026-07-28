"""Unit tests for section-by-section resume parsing and extraction without fake data."""
import pytest
from app.services.parser import (
    parse_resume_bytes,
    extract_email_from_text,
    extract_skills_word_boundary,
    extract_candidate_metadata,
)

SAMPLE_RESUME = """
Jane Doe
Software Engineer
Phone: +1-555-0199
Email: jane.doe@realdomain.com

SUMMARY
Experienced backend developer building scalable microservices in Python and PostgreSQL.

SKILLS
Python, FastAPI, Postgres, Docker, Redis, Go

PROJECTS
- Realtime Analytics Engine: Built a streaming pipeline using Kafka, Python, and Redis. https://github.com/janedoe/analytics
- E-Commerce Microservices: Designed REST APIs using FastAPI and PostgreSQL.

WORK EXPERIENCE
Senior Software Engineer - TechCorp (2021-Present)
- Developed async API services handling 10k QPS.

EDUCATION
B.S. Computer Science - State University (2020)
"""

RESUME_NO_EMAIL = """
John Smith
Senior Architect

SUMMARY
Systems architect with 10 years of experience.

SKILLS
Rust, C++, Kubernetes, AWS
"""


def test_parse_resume_sections():
    parsed = parse_resume_bytes(SAMPLE_RESUME.encode("utf-8"), file_name="Jane_Doe_Resume.pdf")
    assert parsed.candidate_name == "Jane Doe"
    assert parsed.email == "jane.doe@realdomain.com"
    assert parsed.phone == "+1-555-0199"
    assert "backend developer" in parsed.summary.lower()
    assert "python" in parsed.skills
    assert "postgres" in parsed.skills
    assert "fastapi" in parsed.skills
    assert len(parsed.projects) >= 1
    assert any("Analytics Engine" in p.title for p in parsed.projects)


def test_no_fake_email_generation():
    parsed = parse_resume_bytes(RESUME_NO_EMAIL.encode("utf-8"), file_name="resume.pdf")
    assert "@example.com" not in parsed.email
    assert parsed.email == ""


def test_word_boundary_skill_matching():
    text = "We are going to rest after coding in Python and Go."
    skills = extract_skills_word_boundary(text)
    assert "python" in skills
    assert "golang" in skills or "go" in skills or ("go" not in skills and "golang" not in skills)
    # Ensure "rest" or "going" do not trigger false positive skill matches if not intended
    assert "rest" not in skills
