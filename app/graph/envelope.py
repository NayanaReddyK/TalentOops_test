"""Manager <-> sub-agent message envelope with schema validation."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.graph.state import SUB_AGENTS

_VALID_PARTIES = set(SUB_AGENTS) | {"manager"}
EnvelopeKind = Literal["dispatch", "result", "finish", "escalation"]


class Envelope(BaseModel):
    sender: str
    recipient: str
    kind: EnvelopeKind
    body: dict[str, Any] = Field(default_factory=dict)

    def validated(self) -> "Envelope":
        if self.sender not in _VALID_PARTIES:
            raise ValueError(f"Unknown envelope sender: {self.sender!r}")
        if self.recipient not in _VALID_PARTIES and self.recipient != "FINISH":
            raise ValueError(f"Unknown envelope recipient: {self.recipient!r}")
        return self


class EnvelopeValidationError(Exception):
    pass


def make_envelope(sender: str, recipient: str, kind: str, body: dict) -> dict:
    """Build, validate, and return an envelope as a plain dict for graph state."""
    try:
        env = Envelope(sender=sender, recipient=recipient, kind=kind, body=body).validated()
    except (ValidationError, ValueError) as exc:
        raise EnvelopeValidationError(str(exc)) from exc
    return env.model_dump()


def validate_envelope(raw: dict) -> Envelope:
    """Validate an inbound envelope dict; raise on malformed input."""
    try:
        return Envelope(**raw).validated()
    except (ValidationError, ValueError) as exc:
        raise EnvelopeValidationError(str(exc)) from exc
