"""Comprehensive test suite for TalentOps backend."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# Import for type checking
import sys
sys.path.insert(0, '/Users/apple/TalentOops')

from app.config import Settings, get_settings
from app.agents.manager_agent import ManagerAgent
from app.agents.interviewer_fsm import InterviewerFSM, InterviewState, CUES
from app.services.voice_chain import VoiceChain, ConsentError
from app.models.schemas import (
    Envelope,
    ScorecardResult,
    EscalationPayload
)


class TestConfigurationSystem:
    """Comprehensive tests for configuration system."""

    def test_settings_loads_all_environment_variables(self, monkeypatch):
        """Test that Settings loads all environment variables correctly."""
        for key in ["SUPABASE_URL", "SUPABASE_KEY", "GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY"]:
            monkeypatch.delenv(key, raising=False)
        settings = Settings(_env_file=None)
        assert settings.SUPABASE_URL == ""
        assert settings.SUPABASE_KEY == ""
        assert settings.GEMINI_API_KEY == ""
        assert settings.GROQ_API_KEY == ""
        assert settings.OPENROUTER_API_KEY == ""
        assert settings.CORS_ORIGINS == "http://localhost:5173"

    def test_settings_has_property_methods(self):
        """Test that Settings has helper property methods."""
        settings = Settings(_env_file=None)

        assert hasattr(settings, 'cors_origins_list')
        assert hasattr(settings, 'is_offline_mode')

        origins = settings.cors_origins_list
        assert isinstance(origins, list)
        assert origins == ["http://localhost:5173"]

    def test_settings_validation(self):
        """Test Settings type validation."""
        settings = Settings(_env_file=None)

        # All values should be of correct type
        assert isinstance(settings.CONFIDENCE_THRESHOLD, float)
        assert isinstance(settings.TELEMETRY_MAX_RTT_MS, float)
        assert isinstance(settings.TELEMETRY_MAX_JITTER_MS, float)
        assert isinstance(settings.K_ANONYMITY, int)
        assert isinstance(settings.SANDBOX_MAX_SEC, int)

        # Values should be in valid ranges
        assert 0.0 <= settings.CONFIDENCE_THRESHOLD <= 1.0
        assert settings.TELEMETRY_MAX_RTT_MS > 0
        assert settings.TELEMETRY_MAX_JITTER_MS > 0
        assert settings.SANDBOX_MAX_SEC > 0
        assert settings.K_ANONYMITY >= 1


class TestCORSConfiguration:
    """Tests for CORS security configuration."""

    def test_cors_origins_default(self):
        """Test default CORS origins."""
        settings = Settings(_env_file=None)
        assert settings.cors_origins_list == ["http://localhost:5173"]

    def test_cors_origins_multiple_domains(self):
        """Test CORS origins with multiple domains."""
        settings = Settings(CORS_ORIGINS="http://localhost:5173,https://example.com")
        assert settings.cors_origins_list == ["http://localhost:5173", "https://example.com"]

    def test_cors_origins_whitespace_handling(self):
        """Test CORS origins handles whitespace correctly."""
        settings = Settings(CORS_ORIGINS="  http://localhost:5173 ,  https://example.com  ")
        assert settings.cors_origins_list == ["http://localhost:5173", "https://example.com"]

    def test_cors_origins_empty_string(self):
        """Test CORS origins with empty string."""
        settings = Settings(CORS_ORIGINS="")
        assert settings.cors_origins_list == ["http://localhost:5173"]

    def test_offline_mode_default(self):
        """Test offline mode default value."""
        settings = Settings(_env_file=None)
        assert settings.is_offline_mode is False

    def test_offline_mode_true(self):
        """Test offline mode when set to true."""
        settings = Settings(OFFLINE_MODE="true")
        assert settings.is_offline_mode is True

    def test_offline_mode_false(self):
        """Test offline mode when set to false."""
        settings = Settings(OFFLINE_MODE="false")
        assert settings.is_offline_mode is False


class TestManagerAgentFlow:
    """Test Manager Agent business logic flow."""

    def setup_method(self):
        """Setup test fixtures."""
        self.agent = ManagerAgent(role_id="role-1")

    def test_agent_initialization(self):
        """Test agent can be initialized with custom role."""
        assert self.agent.role_id == "role-1"
        assert self.agent.user_email == "manager@example.com"

    def test_valid_escalation_reasons(self):
        """Test all valid escalation reasons."""
        valid_reasons = ["low_confidence", "double_conflict", "no_qualified_candidates",
                        "review_limit_exceeded", "delivery_failure",
                        "protected_attribute_flag", "reschedule_required"]

        for reason in valid_reasons:
            payload = EscalationPayload(reason=reason, candidate_id="candidate-1")
            assert payload.reason == reason

    async def test_invalid_escalation_raises_error(self):
        """Test that invalid escalation reason raises error."""
        with pytest.raises(ValueError):
            await self.agent.escalate(reason="invalid_reason")

    async def test_escalation_creates_event(self, monkeypatch):
        """Test escalation creates database event."""
        mock_insert = AsyncMock(return_value={"id": "event-1", "reason": "low_confidence"})
        monkeypatch.setattr("app.agents.manager_agent.db.insert", mock_insert)

        result = await self.agent.escalate(reason="low_confidence")

        assert result["type"] == "escalation"
        assert result["reason"] == "low_confidence"

    async def test_escalation_sends_email(self, monkeypatch):
        """Test escalation sends email to manager."""
        mock_insert = AsyncMock(return_value={"id": "event-1"})
        monkeypatch.setattr("app.agents.manager_agent.db.insert", mock_insert)

        mock_send = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.send_email", mock_send)

        await self.agent.escalate(reason="low_confidence")

        mock_send.assert_called_once()


class TestInterviewerFSM:
    """Test Interviewer FSM state machine."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_session = MagicMock()
        self.mock_session.next_turn = MagicMock(return_value="[Interviewer] Here's a question")
        self.mock_session.inject_context = MagicMock()

        self.rubric = {
            "competency_1": {
                "description": "Test competency",
                "level_descriptions": {"L1": "Novice", "L2": "Intermediate", "L3": "Expert"}
            }
        }

        self.brief = {
            "candidate_name": "John Doe",
            "background": "Senior developer with 5 years experience"
        }

        self.fsm = InterviewerFSM(
            rubric=self.rubric,
            brief=self.brief,
            session=self.mock_session
        )

    def test_all_states_defined(self):
        """Test that all 8 states are defined."""
        expected_states = [
            InterviewState.SANDBOX,
            InterviewState.OPENING,
            InterviewState.BACKGROUND,
            InterviewState.PROBING,
            InterviewState.FOLLOWUPS,
            InterviewState.RUBRIC_COVERAGE,
            InterviewState.CLOSING,
            InterviewState.POST_CALL
        ]

        assert set(expected_states) == set(InterviewState)

    def test_state_transitions_complete(self):
        """Test complete state transition sequence."""
        states = []
        for _ in range(8):
            next_state = self.fsm.advance()
            states.append(next_state)
            self.fsm.state = next_state

        assert states == [
            InterviewState.OPENING,
            InterviewState.BACKGROUND,
            InterviewState.PROBING,
            InterviewState.FOLLOWUPS,
            InterviewState.RUBRIC_COVERAGE,
            InterviewState.CLOSING,
            InterviewState.POST_CALL,
            InterviewState.SANDBOX
        ]

    def test_state_cues_provide_guidance(self):
        """Test that state cues provide helpful guidance."""
        assert "Open warmly" in CUES[InterviewState.OPENING]
        assert "Background" in CUES[InterviewState.BACKGROUND]
        assert "Probe" in CUES[InterviewState.PROBING]
        assert "Follow up" in CUES[InterviewState.FOLLOWUPS]
        assert "Closing" in CUES[InterviewState.CLOSING]


class TestVoiceChain:
    """Test Voice Chain consent management."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_session = MagicMock()
        self.mock_session.session_id = "test-session-1"
        self.voice_chain = VoiceChain(session=self.mock_session)

    async def test_consent_flow_complete(self):
        """Test complete consent flow."""
        # Open call
        open_result = await self.voice_chain.open_call()
        assert "announcement" in open_result

        # Acknowledge consent
        self.voice_chain.acknowledge_consent()
        assert self.voice_chain._consent is True

        # Interact
        result = await self.voice_chain.interact("Hello")
        assert "[test-session-1]" in result

        # End call
        await self.voice_chain.end_call()

        # Verify metadata
        meta = self.voice_chain.call_meta()
        assert meta["consent_acknowledged"] is True

    async def test_consent_required_before_interaction(self):
        """Test that interaction requires consent."""
        with pytest.raises(ConsentError):
            await self.voice_chain.interact("Hello")

    async def test_consent_error_helpful_message(self):
        """Test that consent error message is helpful."""
        with pytest.raises(ConsentError) as exc_info:
            await self.voice_chain.interact("Hello")

        assert "consent" in str(exc_info.value).lower()
        assert "invalid" in str(exc_info.value).lower()


class TestEnvelopes:
    """Test message envelope validation."""

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
        """Test user envelope rejects wrong speaker."""
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
        """Test candidate envelope rejects wrong speaker."""
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


class TestDataModels:
    """Test Pydantic data models."""

    def test_scorecard_result_validation(self):
        """Test ScorecardResult validation."""
        result = ScorecardResult(
            candidate_id="candidate-1",
            competencies=[],
            overall_fit=0.75,
            needs_human_review=False
        )
        assert result.candidate_id == "candidate-1"
        assert result.overall_fit == 0.75

    def test_scorecard_result_human_review_flag(self):
        """Test ScorecardResult with human review flag."""
        result = ScorecardResult(
            candidate_id="candidate-1",
            competencies=[],
            overall_fit=0.3,
            needs_human_review=True
        )
        assert result.needs_human_review is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])