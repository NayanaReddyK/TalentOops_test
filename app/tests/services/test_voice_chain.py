"""Unit tests for Voice Chain."""
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from app.services.voice_chain import VoiceChain, ConsentError


class TestVoiceChain:
    """Test cases for VoiceChain class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_session = MagicMock()
        self.mock_session.session_id = "test-session-1"
        self.voice_chain = VoiceChain(session=self.mock_session)

    def test_initialization(self):
        """Test VoiceChain initialization."""
        assert self.voice_chain.session == self.mock_session
        assert self.voice_chain._consent is False
        assert self.voice_chain._started is None
        assert self.voice_chain._ended is None

    async def test_open_call_without_consent(self):
        """Test opening a call without consent."""
        result = await self.voice_chain.open_call()

        assert "announcement" in result
        assert result["announcement"] == (
            "This call is recorded and transcribed by TalentOps for interview evaluation "
            "and audit purposes. By continuing, you consent to this recording. "
            "Say 'I agree' to continue, or leave the call now."
        )
        assert result["session_id"] == "test-session-1"
        assert self.voice_chain._started is not None

    async def test_open_call_with_consent_already_set(self):
        """Test opening a call when consent is already set."""
        self.voice_chain.acknowledge_consent()

        result = await self.voice_chain.open_call()

        assert self.voice_chain._started is not None
        assert result["announcement"] == (
            "This call is recorded and transcribed by TalentOps for interview evaluation "
            "and audit purposes. By continuing, you consent to this recording. "
            "Say 'I agree' to continue, or leave the call now."
        )

    def test_consent_acknowledgment(self):
        """Test that consent acknowledgment sets flag."""
        assert self.voice_chain._consent is False

        self.voice_chain.acknowledge_consent()

        assert self.voice_chain._consent is True

    async def test_consent_not_set_interaction(self):
        """Test that interaction raises error when consent not set."""
        with pytest.raises(ConsentError, match="call invalid: consent_acknowledged is false"):
            await self.voice_chain.interact("Hello")

    async def test_interact_with_consent(self):
        """Test successful interaction after consent."""
        self.voice_chain.acknowledge_consent()

        result = await self.voice_chain.interact("Tell me about your experience")

        assert result == "[test-session-1] Tell me about your experience"

    async def test_interact_preserves_original_text(self):
        """Test that original text is preserved in interaction."""
        self.voice_chain.acknowledge_consent()

        original_text = "I have 5 years of experience"
        result = await self.voice_chain.interact(original_text)

        assert original_text in result
        assert "[test-session-1]" in result

    async def test_end_call(self):
        """Test ending a call."""
        self.voice_chain._started = datetime.now(timezone.utc).isoformat()

        await self.voice_chain.end_call()

        assert self.voice_chain._ended is not None

    async def test_end_call_without_start(self):
        """Test ending a call that was never started."""
        await self.voice_chain.end_call()

        assert self.voice_chain._ended is not None

    def test_call_meta_without_consent(self):
        """Test call metadata when consent not set."""
        meta = self.voice_chain.call_meta()

        assert meta["consent_acknowledged"] is False
        assert meta["started_ts"] == ""
        assert meta["ended_ts"] is not None

    def test_call_meta_with_consent(self):
        """Test call metadata when consent is set."""
        self.voice_chain.acknowledge_consent()
        self.voice_chain._started = "2024-01-01T00:00:00Z"
        self.voice_chain._ended = "2024-01-01T00:30:00Z"

        meta = self.voice_chain.call_meta()

        assert meta["consent_acknowledged"] is True
        assert meta["started_ts"] == "2024-01-01T00:00:00Z"
        assert meta["ended_ts"] == "2024-01-01T00:30:00Z"

    async def test_consent_error_message(self):
        """Test that consent error has helpful message."""
        with pytest.raises(ConsentError) as exc_info:
            await self.voice_chain.interact("Hello")

        assert "consent_acknowledged is false" in str(exc_info.value)
        assert "consent" in str(exc_info.value).lower()

    async def test_interact_with_new_session(self):
        """Test interaction with session that has different ID."""
        self.mock_session.session_id = "new-session-2"
        self.voice_chain.acknowledge_consent()

        result = await self.voice_chain.interact("New message")

        assert result == "[new-session-2] New message"

    async def test_multiple_interactions(self):
        """Test multiple consecutive interactions."""
        self.voice_chain.acknowledge_consent()

        first_result = await self.voice_chain.interact("First message")
        second_result = await self.voice_chain.interact("Second message")

        assert "[test-session-1]" in first_result
        assert "[test-session-1]" in second_result

    async def test_end_call_updates_metadata(self):
        """Test that ending call updates metadata correctly."""
        self.voice_chain._started = datetime.now(timezone.utc).isoformat()
        await self.voice_chain.end_call()

        meta = self.voice_chain.call_meta()

        assert meta["consent_acknowledged"] is False
        assert meta["started_ts"] != ""
        assert meta["ended_ts"] != ""
        assert meta["ended_ts"] >= meta["started_ts"]


class TestVoiceChainConsentFlow:
    """Test the complete consent flow."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_session = MagicMock()
        self.mock_session.session_id = "session-1"
        self.voice_chain = VoiceChain(session=self.mock_session)

    async def test_full_consent_flow(self):
        """Test complete consent flow: open, acknowledge, interact, end."""
        # Open call
        open_result = await self.voice_chain.open_call()
        assert open_result["announcement"] is not None

        # Acknowledge consent
        self.voice_chain.acknowledge_consent()
        assert self.voice_chain._consent is True

        # Interact
        interact_result = await self.voice_chain.interact("Hello")
        assert interact_result == "[session-1] Hello"

        # End call
        await self.voice_chain.end_call()

        # Check metadata
        meta = self.voice_chain.call_meta()
        assert meta["consent_acknowledged"] is True
        assert meta["started_ts"] != ""
        assert meta["ended_ts"] != ""

    async def test_consent_flow_with_errors(self):
        """Test consent flow with various error conditions."""
        # Try to interact without consent
        with pytest.raises(ConsentError):
            await self.voice_chain.interact("Hello")

        # Then acknowledge consent
        self.voice_chain.acknowledge_consent()

        # Now interact should work
        result = await self.voice_chain.interact("Hello")
        assert "[session-1]" in result


class TestVoiceChainTimestamps:
    """Test timestamp handling in VoiceChain."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_session = MagicMock()
        self.mock_session.session_id = "session-1"
        self.voice_chain = VoiceChain(session=self.mock_session)

    async def test_timestamp_is_iso_format(self):
        """Test that timestamps are in ISO format."""
        await self.voice_chain.open_call()
        start_ts = self.voice_chain._started

        assert isinstance(start_ts, str)
        assert "T" in start_ts  # ISO format contains 'T'

    async def test_timestamp_format_consistency(self):
        """Test that timestamps follow consistent format."""
        for _ in range(3):
            await self.voice_chain.open_call()
            start_ts = self.voice_chain._started

        await self.voice_chain.end_call()
        end_ts = self.voice_chain._ended
        assert isinstance(end_ts, str)
        assert "T" in end_ts