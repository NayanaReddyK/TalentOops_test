"""Unit tests for Pydantic models and schemas."""
import pytest

import pydantic
from app.models.schemas import (
    Envelope,
    EvidenceQuote,
    CompetencyScore,
    ScorecardResult,
    QuestionRecord,
    CallMeta,
    InterviewerResult,
    EscalationPayload,
    CalibrationRecord,
)


class TestEnvelope:
    """Test cases for Envelope model."""

    def test_valid_user_envelope(self):
        """Test valid user voice envelope."""
        envelope = Envelope(
            msg_id="test-1",
            ts="2024-01-01T00:00:00Z",
            from_agent="manager",
            to="user",
            type="task.assign",
            role_id="role-1",
            voice_context="user",
            payload={"task": "create_interview"}
        )
        assert envelope.from_agent == "manager"
        assert envelope.voice_context == "user"

    def test_valid_candidate_envelope(self):
        """Test valid candidate voice envelope."""
        envelope = Envelope(
            msg_id="test-2",
            ts="2024-01-01T00:00:00Z",
            from_agent="interviewer",
            to="candidate",
            type="task.assign",
            role_id="role-1",
            candidate_id="candidate-1",
            voice_context="candidate",
            payload={"question": "Tell me about yourself"}
        )
        assert envelope.from_agent == "interviewer"
        assert envelope.voice_context == "candidate"

    def test_invalid_user_envelope_from_wrong_agent(self):
        """Test that user envelope rejects wrong speaker."""
        with pytest.raises(ValueError, match="voice_context 'user' valid only when speaker is manager"):
            Envelope(
                msg_id="test-3",
                ts="2024-01-01T00:00:00Z",
                from_agent="interviewer",
                to="user",
                type="task.assign",
                role_id="role-1",
                voice_context="user",
                payload={}
            )

    def test_invalid_candidate_envelope_from_wrong_agent(self):
        """Test that candidate envelope rejects wrong speaker."""
        with pytest.raises(ValueError, match="voice_context 'candidate' valid only when speaker is interviewer"):
            Envelope(
                msg_id="test-4",
                ts="2024-01-01T00:00:00Z",
                from_agent="manager",
                to="candidate",
                type="task.assign",
                role_id="role-1",
                candidate_id="candidate-1",
                voice_context="candidate",
                payload={}
            )

    def test_envelope_missing_required_fields(self):
        """Test envelope validation with missing required fields."""
        with pytest.raises(pydantic.ValidationError):
            Envelope(
                msg_id="test-5",
                # missing ts, from_agent, to, etc.
                payload={}
            )


class TestEvidenceQuote:
    """Test cases for EvidenceQuote model."""

    def test_valid_evidence_quote(self):
        """Test valid evidence quote."""
        quote = EvidenceQuote(
            quote="I implemented a Redis caching layer",
            char_start=0,
            char_end=35,
            speaker="candidate",
            validated=True
        )
        assert quote.quote == "I implemented a Redis caching layer"
        assert quote.speaker == "candidate"
        assert quote.validated is True


class TestCompetencyScore:
    """Test cases for CompetencyScore model."""

    def test_valid_competency_score(self):
        """Test valid competency score."""
        score = CompetencyScore(
            competency_id="system-design",
            demonstrated_level="L2",
            evidence_quotes=[]
        )
        assert score.competency_id == "system-design"
        assert score.demonstrated_level == "L2"

    def test_insufficient_evidence_level(self):
        """Test insufficient evidence level."""
        score = CompetencyScore(
            competency_id="testing",
            demonstrated_level="insufficient_evidence",
            evidence_quotes=[]
        )
        assert score.demonstrated_level == "insufficient_evidence"


class TestScorecardResult:
    """Test cases for ScorecardResult model."""

    def test_valid_scorecard_result(self):
        """Test valid scorecard result."""
        result = ScorecardResult(
            candidate_id="candidate-1",
            competencies=[],
            overall_fit=0.75,
            needs_human_review=False
        )
        assert result.candidate_id == "candidate-1"
        assert result.overall_fit == 0.75
        assert result.needs_human_review is False

    def test_needs_human_review_flag(self):
        """Test scorecard result with human review flag."""
        result = ScorecardResult(
            candidate_id="candidate-2",
            competencies=[],
            overall_fit=0.3,
            needs_human_review=True
        )
        assert result.needs_human_review is True


class TestQuestionRecord:
    """Test cases for QuestionRecord model."""

    def test_valid_question_record(self):
        """Test valid question record."""
        record = QuestionRecord(
            q_id="q-1",
            ts="2024-01-01T00:00:00Z",
            competency_id="programming",
            question_text="What is your experience with Python?",
            rating=None,
            difficulty_estimate=0.7,
            confidence=0.8,
            flags=[]
        )
        assert record.q_id == "q-1"
        assert record.rating is None
        assert record.difficulty_estimate == 0.7
        assert record.confidence == 0.8

    def test_question_with_flags(self):
        """Test question record with flags."""
        record = QuestionRecord(
            q_id="q-2",
            ts="2024-01-01T00:00:00Z",
            competency_id="communication",
            question_text="How do you handle conflict?",
            rating=None,
            difficulty_estimate=0.5,
            confidence=0.6,
            flags=["too_complex", "ambiguous"]
        )
        assert len(record.flags) == 2


class TestCallMeta:
    """Test cases for CallMeta model."""

    def test_valid_call_meta(self):
        """Test valid call metadata."""
        meta = CallMeta(
            started_ts="2024-01-01T00:00:00Z",
            ended_ts="2024-01-01T00:30:00Z",
            consent_acknowledged=True,
            sandbox_telemetry_ref="telemetry-1"
        )
        assert meta.consent_acknowledged is True
        assert meta.started_ts == "2024-01-01T00:00:00Z"


class TestInterviewerResult:
    """Test cases for InterviewerResult model."""

    def test_valid_interviewer_result(self):
        """Test valid interviewer result."""
        result = InterviewerResult(
            candidate_id="candidate-1",
            transcript_ref="transcript-1",
            questions=[],
            anomaly_flags=[],
            rubric_coverage=[],
            needs_human_review=False,
            call_meta=CallMeta(
                started_ts="2024-01-01T00:00:00Z",
                ended_ts="2024-01-01T00:30:00Z",
                consent_acknowledged=True
            )
        )
        assert result.candidate_id == "candidate-1"
        assert result.transcript_ref == "transcript-1"
        assert result.needs_human_review is False


class TestEscalationPayload:
    """Test cases for EscalationPayload model."""

    def test_valid_escalation_reasons(self):
        """Test valid escalation reasons."""
        reasons = ["low_confidence", "double_conflict", "no_qualified_candidates",
                   "review_limit_exceeded", "delivery_failure",
                   "protected_attribute_flag", "reschedule_required"]

        for reason in reasons:
            payload = EscalationPayload(
                reason=reason,
                candidate_id="candidate-1" if reason != "delivery_failure" else None
            )
            assert payload.reason == reason

    def test_invalid_escalation_reason(self):
        """Test that invalid escalation reason raises error."""
        with pytest.raises(pydantic.ValidationError):
            EscalationPayload(
                reason="invalid_reason",
                candidate_id="candidate-1"
            )


class TestCalibrationRecord:
    """Test cases for CalibrationRecord model."""

    def test_valid_calibration_record(self):
        """Test valid calibration record."""
        record = CalibrationRecord(
            interview_id="interview-1",
            rtt_ms=250.5,
            jitter_ms=15.3,
            audio_level=0.85,
            passed=True
        )
        assert record.rtt_ms == 250.5
        assert record.jitter_ms == 15.3
        assert record.audio_level == 0.85
        assert record.passed is True