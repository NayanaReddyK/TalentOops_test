"""Unit tests for Scorecard Agent."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.scorecard_agent import ScorecardAgent, _parse_quotes, EXTRACT_PROMPT


class TestScorecardAgent:
    """Test cases for ScorecardAgent class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.agent = ScorecardAgent(max_retries=2)

    def test_initialization(self):
        """Test ScorecardAgent initialization."""
        assert self.agent.max_retries == 2

    def test_initialization_custom_retries(self):
        """Test ScorecardAgent with custom max retries."""
        custom_agent = ScorecardAgent(max_retries=3)
        assert custom_agent.max_retries == 3

    def test_parse_quotes_empty_string(self):
        """Test parsing quotes from empty string."""
        result = _parse_quotes("")
        assert result == []

    def test_parse_quotes_no_brackets(self):
        """Test parsing quotes when no brackets found."""
        result = _parse_quotes("Some random text here")
        assert result == []

    def test_parse_quotes_partial_brackets(self):
        """Test parsing quotes with incomplete brackets."""
        result = _parse_quotes("This is incomplete [")
        assert result == []

    def test_parse_quotes_valid_json(self):
        """Test parsing valid JSON bracket content."""
        json_content = '[{"competency_id": "test", "quote": "Test quote", "speaker": "candidate"}]'
        result = _parse_quotes(json_content)

        assert len(result) == 1
        assert result[0]["competency_id"] == "test"
        assert result[0]["quote"] == "Test quote"
        assert result[0]["speaker"] == "candidate"

    def test_parse_quotes_multiple_items(self):
        """Test parsing multiple quote items."""
        json_content = (
            '[{"competency_id": "test1", "quote": "Quote 1", "speaker": "candidate"}, '
            '{"competency_id": "test2", "quote": "Quote 2", "speaker": "interviewer"}]'
        )
        result = _parse_quotes(json_content)

        assert len(result) == 2
        assert result[0]["competency_id"] == "test1"
        assert result[1]["competency_id"] == "test2"

    def test_parse_quotes_invalid_json(self):
        """Test parsing invalid JSON returns empty list."""
        result = _parse_quotes("[invalid json}")
        assert result == []

    def test_parse_quotes_invalid_structure(self):
        """Test parsing JSON with invalid structure returns empty list."""
        result = _parse_quotes('[{"competency_id": "test"}')  # Missing closing bracket
        assert result == []

    def test_extract_prompt_exists(self):
        """Test that EXTRACT_PROMPT is defined."""
        assert isinstance(EXTRACT_PROMPT, str)
        assert len(EXTRACT_PROMPT) > 0
        assert "extract" in EXTRACT_PROMPT.lower()
        assert "competency" in EXTRACT_PROMPT.lower()

    async def test_extract_quotes_from_valid_transcript(self, monkeypatch):
        """Test extraction from valid transcript with valid response."""
        mock_transcript = "Candidate mentioned implementing Redis caching"
        mock_rubric = {"competency_id": "system-design"}

        mock_response = (
            '[{"competency_id": "system-design", "quote": "I implemented Redis caching", '
            '"speaker": "candidate"}]'
        )

        mock_chat = AsyncMock(return_value=mock_response)
        monkeypatch.setattr("app.agents.scorecard_agent.openrouter_chat", mock_chat)
        monkeypatch.setattr("app.agents.scorecard_agent.groq_chat", mock_chat)

        result = await self.agent._extract(mock_transcript, mock_rubric)

        assert len(result) == 1
        assert result[0]["competency_id"] == "system-design"
        assert result[0]["quote"] == "I implemented Redis caching"

    async def test_extract_handles_openrouter_primary(self, monkeypatch):
        """Test that OpenRouter is tried first in extraction."""
        mock_transcript = "Test transcript"
        mock_rubric = {}

        # First call fails, second succeeds
        openrouter_chat = AsyncMock(side_effect=Exception("First call failed"))
        groq_chat = AsyncMock(return_value='[{"competency_id": "test", "quote": "quote", "speaker": "candidate"}]')

        monkeypatch.setattr("app.agents.scorecard_agent.openrouter_chat", openrouter_chat)
        monkeypatch.setattr("app.agents.scorecard_agent.groq_chat", groq_chat)

        result = await self.agent._extract(mock_transcript, mock_rubric)

        assert openrouter_chat.call_count == 1
        assert groq_chat.call_count == 1

    async def test_extract_allows_retry(self, monkeypatch):
        """Test that extraction allows retries on failure."""
        mock_transcript = "Test transcript"
        mock_rubric = {}

        # All calls fail
        mock_chat = AsyncMock(side_effect=Exception("All failed"))

        monkeypatch.setattr("app.agents.scorecard_agent.openrouter_chat", mock_chat)
        monkeypatch.setattr("app.agents.scorecard_agent.groq_chat", mock_chat)

        with pytest.raises(Exception):
            await self.agent._extract(mock_transcript, mock_rubric)

    async def test_extract_json_mode_parameter(self, monkeypatch):
        """Test that json_mode parameter is passed to chat clients."""
        mock_transcript = "Test transcript"
        mock_rubric = {}

        mock_chat = AsyncMock(return_value='[{"competency_id": "test", "quote": "quote", "speaker": "candidate"}]')

        monkeypatch.setattr("app.agents.scorecard_agent.groq_chat", mock_chat)
        monkeypatch.setattr("app.agents.scorecard_agent.openrouter_chat", mock_chat)

        await self.agent._extract(mock_transcript, mock_rubric)

        # Check that json_mode=True was passed
        call_args = mock_chat.call_args
        assert call_args is not None

    async def test_extract_handles_empty_transcript(self, monkeypatch):
        """Test extraction with empty transcript."""
        mock_rubric = {"competency_id": "test"}

        mock_chat = AsyncMock(return_value='[]')
        monkeypatch.setattr("app.agents.scorecard_agent.openrouter_chat", mock_chat)
        monkeypatch.setattr("app.agents.scorecard_agent.groq_chat", mock_chat)

        result = await self.agent._extract("", mock_rubric)

        assert result == []

    async def test_extract_handles_empty_rubric(self, monkeypatch):
        """Test extraction with empty rubric."""
        mock_transcript = "Candidate mentioned testing"

        mock_chat = AsyncMock(return_value='[{"competency_id": "test", "quote": "quote", "speaker": "candidate"}]')
        monkeypatch.setattr("app.agents.scorecard_agent.openrouter_chat", mock_chat)
        monkeypatch.setattr("app.agents.scorecard_agent.groq_chat", mock_chat)

        result = await self.agent._extract(mock_transcript, {})

        assert isinstance(result, list)

    async def test_extract_validates_result_structure(self, monkeypatch):
        """Test that extracted quotes are validated."""
        mock_transcript = "Test"
        mock_rubric = {}

        # Return invalid structure (no quotes)
        mock_chat = AsyncMock(return_value='[{"competency_id": "test"}]')
        monkeypatch.setattr("app.agents.scorecard_agent.openrouter_chat", mock_chat)
        monkeypatch.setattr("app.agents.scorecard_agent.groq_chat", mock_chat)

        result = await self.agent._extract(mock_transcript, mock_rubric)

        assert result == []

    async def test_extract_validates_has_quote_field(self, monkeypatch):
        """Test that extracted items without quotes are filtered."""
        mock_transcript = "Test"
        mock_rubric = {}

        # Return items without quotes field
        mock_chat = AsyncMock(return_value='[{"competency_id": "test", "speaker": "candidate"}]')
        monkeypatch.setattr("app.agents.scorecard_agent.openrouter_chat", mock_chat)
        monkeypatch.setattr("app.agents.scorecard_agent.groq_chat", mock_chat)

        result = await self.agent._extract(mock_transcript, mock_rubric)

        assert result == []


class TestScorecardAgentMinQuoteLength:
    """Test the minimum quote length requirement."""

    def setup_method(self):
        """Setup test fixtures."""
        self.agent = ScorecardAgent(max_retries=2)

    def test_min_quote_length_defined(self):
        """Test that MIN_QUOTE_LEN is defined."""
        from app.agents.scorecard_agent import MIN_QUOTE_LEN

        assert isinstance(MIN_QUOTE_LEN, int)
        assert MIN_QUOTE_LEN > 0

    def test_min_quote_length_validates_quote_length(self, monkeypatch):
        """Test that quotes shorter than minimum are filtered."""
        mock_transcript = "Candidate mentioned Redis"
        item = {"competency_id": "test", "quote": "Redis", "speaker": "candidate"}

        validated = self.agent._validate(mock_transcript, item)
        assert validated is None