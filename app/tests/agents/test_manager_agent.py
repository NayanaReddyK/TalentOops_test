"""Unit tests for Manager Agent."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.manager_agent import ManagerAgent, VALID_REASONS


class TestManagerAgent:
    """Test cases for ManagerAgent class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.manager_agent = ManagerAgent(role_id="role-1", user_email="manager@example.com")

    def test_initialization(self):
        """Test agent initialization."""
        assert self.manager_agent.role_id == "role-1"
        assert self.manager_agent.user_email == "manager@example.com"

    def test_valid_escalation_reasons(self):
        """Test that only valid escalation reasons are accepted."""
        assert VALID_REASONS == {
            "low_confidence",
            "double_conflict",
            "no_qualified_candidates",
            "review_limit_exceeded",
            "delivery_failure",
            "protected_attribute_flag",
            "reschedule_required"
        }

    async def test_escalate_valid_reason(self, monkeypatch):
        """Test successful escalation with valid reason."""
        # Mock database insert
        mock_insert = AsyncMock()
        mock_insert.return_value = {"id": "event-1", "type": "escalation", "reason": "low_confidence"}
        monkeypatch.setattr("app.agents.manager_agent.db.insert", mock_insert)

        # Mock email handler
        mock_send_email = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.send_email", mock_send_email)

        # Test escalation
        result = await self.manager_agent.escalate(
            reason="low_confidence",
            details_ref="transcript-1",
            candidate_id="candidate-1"
        )

        assert result["type"] == "escalation"
        assert result["reason"] == "low_confidence"
        assert result["candidate_id"] == "candidate-1"
        assert result["details_ref"] == "transcript-1"

    async def test_escalate_invalid_reason(self):
        """Test that invalid escalation reason raises ValueError."""
        with pytest.raises(ValueError, match="unknown escalation reason"):
            await self.manager_agent.escalate(reason="invalid_reason")

    async def test_on_interviewer_result_needs_review(self, monkeypatch):
        """Test escalation when interviewer result needs human review."""
        mock_insert = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.db.insert", mock_insert)

        mock_send_email = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.send_email", mock_send_email)

        result = {
            "needs_human_review": True,
            "transcript_ref": "transcript-1",
            "candidate_id": "candidate-1"
        }

        escalation = await self.manager_agent.on_interviewer_result(result)

        assert escalation is not None
        assert escalation["type"] == "escalation"
        assert escalation["reason"] == "low_confidence"
        mock_send_email.assert_called_once()

    async def test_on_interviewer_result_no_review_needed(self, monkeypatch):
        """Test no escalation when interviewer result is good."""
        mock_insert = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.db.insert", mock_insert)

        mock_send_email = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.send_email", mock_send_email)

        result = {
            "needs_human_review": False,
            "transcript_ref": "transcript-1",
            "candidate_id": "candidate-1"
        }

        escalation = await self.manager_agent.on_interviewer_result(result)

        assert escalation is None
        mock_insert.assert_not_called()
        mock_send_email.assert_not_called()

    async def test_on_interviewer_result_missing_needs_review(self, monkeypatch):
        """Test no escalation when 'needs_human_review' key is missing."""
        mock_insert = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.db.insert", mock_insert)

        mock_send_email = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.send_email", mock_send_email)

        result = {
            "transcript_ref": "transcript-1",
            "candidate_id": "candidate-1"
        }

        escalation = await self.manager_agent.on_interviewer_result(result)

        assert escalation is None
        mock_insert.assert_not_called()
        mock_send_email.assert_not_called()

    async def test_on_scheduling_with_conflicts(self, monkeypatch):
        """Test escalation when scheduling has multiple conflicts."""
        mock_insert = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.db.insert", mock_insert)

        mock_send_email = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.send_email", mock_send_email)

        escalation = await self.manager_agent.on_scheduling(
            status="rejected",
            conflict_count=2,
            candidate_id="candidate-1"
        )

        assert escalation is not None
        assert escalation["reason"] == "double_conflict"
        assert escalation["candidate_id"] == "candidate-1"
        mock_send_email.assert_called_once()

    async def test_on_scheduling_status_rejected(self, monkeypatch):
        """Test escalation when status is rejected."""
        mock_insert = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.db.insert", mock_insert)

        mock_send_email = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.send_email", mock_send_email)

        escalation = await self.manager_agent.on_scheduling(
            status="rejected",
            conflict_count=1,
            candidate_id="candidate-1"
        )

        assert escalation is not None
        assert escalation["reason"] == "double_conflict"

    async def test_on_scheduling_no_conflicts(self, monkeypatch):
        """Test no escalation when scheduling is successful."""
        mock_insert = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.db.insert", mock_insert)

        mock_send_email = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.send_email", mock_send_email)

        escalation = await self.manager_agent.on_scheduling(
            status="confirmed",
            conflict_count=0,
            candidate_id="candidate-1"
        )

        assert escalation is None
        mock_send_email.assert_not_called()

    async def test_on_sourcing_cycle_no_candidates(self, monkeypatch):
        """Test escalation when no qualified candidates after multiple cycles."""
        mock_insert = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.db.insert", mock_insert)

        mock_send_email = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.send_email", mock_send_email)

        escalation = await self.manager_agent.on_sourcing_cycle(cycles=2, qualified_count=0)

        assert escalation is not None
        assert escalation["reason"] == "no_qualified_candidates"
        mock_send_email.assert_called_once()

    async def test_on_sourcing_cycle_has_candidates(self, monkeypatch):
        """Test no escalation when qualified candidates are found."""
        mock_insert = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.db.insert", mock_insert)

        mock_send_email = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.send_email", mock_send_email)

        escalation = await self.manager_agent.on_sourcing_cycle(cycles=1, qualified_count=1)

        assert escalation is None
        mock_send_email.assert_not_called()

    async def test_on_sourcing_cycle_one_cycle(self, monkeypatch):
        """Test no escalation with only one sourcing cycle."""
        mock_insert = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.db.insert", mock_insert)

        mock_send_email = AsyncMock()
        monkeypatch.setattr("app.agents.manager_agent.send_email", mock_send_email)

        escalation = await self.manager_agent.on_sourcing_cycle(cycles=1, qualified_count=0)

        assert escalation is None
        mock_send_email.assert_not_called()

    def test_custom_user_email(self):
        """Test agent with custom user email."""
        custom_agent = ManagerAgent(role_id="role-1", user_email="custom-manager@example.com")
        assert custom_agent.user_email == "custom-manager@example.com"