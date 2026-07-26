"""Pydantic models mirroring 04-API-EVENT-CONTRACT.md (contract v1.2.0)."""
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class Envelope(BaseModel):
    """§4.1 message envelope with message-level voice-ownership validation."""
    msg_id: str
    ts: str
    from_agent: str = Field(alias="from")
    to: str
    type: Literal["task.assign", "task.result", "task.error", "event.completion", "escalation"]
    role_id: str
    candidate_id: str | None = None
    voice_context: Literal["user", "candidate"] | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _voice_ownership(self) -> "Envelope":
        if self.voice_context == "user" and self.from_agent != "manager":
            raise ValueError("voice_context 'user' valid only when speaker is manager")
        if self.voice_context == "candidate" and self.from_agent != "interviewer":
            raise ValueError("voice_context 'candidate' valid only when speaker is interviewer")
        return self


class EvidenceQuote(BaseModel):
    quote: str
    char_start: int
    char_end: int
    speaker: Literal["candidate", "interviewer"]
    validated: bool


class CompetencyScore(BaseModel):
    competency_id: str
    demonstrated_level: Literal["L1", "L2", "L3", "insufficient_evidence"]
    evidence_quotes: list[EvidenceQuote] = Field(default_factory=list)


class ScorecardResult(BaseModel):
    candidate_id: str
    competencies: list[CompetencyScore]
    overall_fit: float
    needs_human_review: bool


class QuestionRecord(BaseModel):
    q_id: str
    ts: str
    competency_id: str
    question_text: str
    rating: float | None = None  # always None in-call — scoring lives in Phase 2 (D19)
    difficulty_estimate: float
    confidence: float
    flags: list[str] = Field(default_factory=list)


class CallMeta(BaseModel):
    started_ts: str
    ended_ts: str
    consent_acknowledged: bool
    sandbox_telemetry_ref: str | None = None


class InterviewerResult(BaseModel):
    candidate_id: str | None
    transcript_ref: str
    questions: list[QuestionRecord]
    anomaly_flags: list[str] = Field(default_factory=list)
    rubric_coverage: list[dict[str, Any]] = Field(default_factory=list)
    needs_human_review: bool
    call_meta: CallMeta


class EscalationPayload(BaseModel):
    reason: Literal[
        "low_confidence", "double_conflict", "no_qualified_candidates",
        "review_limit_exceeded", "delivery_failure", "protected_attribute_flag",
        "reschedule_required",
    ]
    details_ref: str | None = None
    candidate_id: str | None = None


class CalibrationRecord(BaseModel):
    interview_id: str
    rtt_ms: float
    jitter_ms: float
    audio_level: float
    passed: bool
