"""Frozen rubric generation and immutability."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, Field

from app.llm.client import get_llm_client


class Competency(BaseModel):
    name: str
    description: str
    weight: float = Field(ge=0.0, le=1.0)


class Rubric(BaseModel):
    run_id: str
    standard: str
    competencies: list[Competency]
    content_hash: str = ""

    def canonical(self) -> str:
        """Deterministic serialization used for hashing (excludes the hash)."""
        payload = {
            "run_id": self.run_id,
            "standard": self.standard,
            "competencies": [c.model_dump() for c in self.competencies],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def compute_hash(self) -> str:
        return hashlib.sha256(self.canonical().encode()).hexdigest()

    def frozen(self) -> "Rubric":
        return self.model_copy(update={"content_hash": self.compute_hash()})


class RubricDriftError(Exception):
    """Raised when a rubric mutation is attempted after freezing."""


def generate_rubric(run_id: str, standard: str) -> Rubric:
    """Derive a frozen rubric from the user's evaluation standard via the LLM."""
    llm = get_llm_client()
    result: dict[str, Any] = llm.complete_json(
        system=(
            "You are an evaluation designer. Given a hiring standard, produce a "
            "fair, competency-based rubric. Weights must sum to ~1.0."
        ),
        user=standard,
        schema_hint={"competencies": "list[str]", "summary": "str"},
    )

    names = result.get("competencies") or ["technical", "communication", "problem-solving"]
    competencies = []
    
    if names and all(isinstance(n, dict) for n in names):
        for n in names:
            name = n.get("name", "Unknown")
            description = n.get("description", f"Assess candidate on: {name}")
            weight = n.get("weight", round(1.0 / len(names), 4))
            competencies.append(Competency(name=name, description=description, weight=weight))
    else:
        weight = round(1.0 / len(names), 4) if names else 1.0
        for n in names:
            name = n if isinstance(n, str) else str(n)
            competencies.append(Competency(name=name, description=f"Assess candidate on: {name}", weight=weight))
    rubric = Rubric(run_id=run_id, standard=standard, competencies=competencies)
    return rubric.frozen()


def assert_unchanged(frozen: Rubric, candidate: Rubric) -> None:
    """Guard: a candidate rubric must match the frozen one's hash."""
    if candidate.compute_hash() != frozen.content_hash:
        raise RubricDriftError(
            f"Rubric drift for run {frozen.run_id}: "
            f"{frozen.content_hash[:12]} != {candidate.compute_hash()[:12]}"
        )
