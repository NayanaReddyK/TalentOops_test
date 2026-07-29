"""Unit tests for Interviewer FSM."""
import pytest
from unittest.mock import MagicMock
from app.agents.interviewer_fsm import (
    InterviewerFSM,
    InterviewState,
    CUES
)


class TestInterviewState:
    """Test cases for InterviewState enum."""

    def test_state_enum_values(self):
        """Test that all state enum values are defined."""
        assert len(InterviewState) == 8
        assert InterviewState.SANDBOX == 0
        assert InterviewState.OPENING == 1
        assert InterviewState.BACKGROUND == 2
        assert InterviewState.PROBING == 3
        assert InterviewState.FOLLOWUPS == 4
        assert InterviewState.RUBRIC_COVERAGE == 5
        assert InterviewState.CLOSING == 6
        assert InterviewState.POST_CALL == 7

    def test_state_cues_exist(self):
        """Test that all states have corresponding cues."""
        for state in InterviewState:
            assert state in CUES
            assert isinstance(CUES[state], str)
            assert len(CUES[state]) > 0


class TestInterviewerFSM:
    """Test cases for InterviewerFSM class."""

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

    def test_initialization(self):
        """Test FSM initialization."""
        assert self.fsm.rubric == self.rubric
        assert self.fsm.brief == self.brief
        assert self.fsm.session == self.mock_session
        assert self.fsm.state == InterviewState.SANDBOX
        assert self.fsm.threshold == 0.65
        assert len(self.fsm.transitions) == 1

    def test_initial_transitions(self):
        """Test initial state transitions."""
        assert self.fsm.state in self.fsm.transitions

    def test_advance_from_sandbox(self):
        """Test advancing from SANDBOX state."""
        result = self.fsm.advance()
        assert result == InterviewState.OPENING
        assert self.fsm.state == InterviewState.OPENING
        assert InterviewState.OPENING in self.fsm.transitions

    def test_advance_from_closing(self):
        """Test advancing from CLOSING state."""
        # First advance to CLOSING
        for _ in range(InterviewState.OPENING.value):
            self.fsm.advance()

        # Now test from CLOSING
        self.fsm.state = InterviewState.CLOSING
        result = self.fsm.advance()
        assert result == InterviewState.POST_CALL

    def test_advance_from_post_call(self):
        """Test advancing from POST_CALL state."""
        # First advance to POST_CALL
        for _ in range(InterviewState.CLOSING.value + 1):
            self.fsm.advance()

        # Now test from POST_CALL
        self.fsm.state = InterviewState.POST_CALL
        result = self.fsm.advance()
        assert result == InterviewState.SANDBOX

    def test_transitions_recorded(self):
        """Test that state transitions are recorded."""
        assert len(self.fsm.transitions) > 0

    def test_answer_tracking(self):
        """Test that answers are tracked."""
        assert len(self.fsm._answers) == 0

    def test_question_tracking(self):
        """Test that questions are tracked."""
        assert len(self.fsm._questions) == 0

    def test_cues_available(self):
        """Test that state cues are available."""
        assert CUES[InterviewState.OPENING] == "Open warmly: intro, set context, put the candidate at ease."
        assert CUES[InterviewState.PROBING] == "Probe brief competencies against their actual, specific usage."

    def test_consistency_check(self):
        """Test FSM consistency check."""
        assert self.fsm.state == InterviewState.SANDBOX
        assert self.fsm.state in self.fsm.transitions

    def test_transition_sequence(self):
        """Test complete transition sequence."""
        start_state = self.fsm.state
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


class TestInterviewerFSMCustomThreshold:
    """Test FSM with custom threshold."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_session = MagicMock()
        self.mock_session.next_turn = MagicMock(return_value="[Interviewer] Here's a question")

        self.rubric = {
            "competency_1": {"description": "Test competency"}
        }

        self.brief = {"candidate_name": "Test Candidate"}

        self.fsm = InterviewerFSM(
            rubric=self.rubric,
            brief=self.brief,
            session=self.mock_session,
            confidence_threshold=0.8
        )

    def test_custom_threshold_used(self):
        """Test that custom threshold is used."""
        assert self.fsm.threshold == 0.8


class TestInterviewerFSMInvalidState:
    """Test FSM with invalid operations."""

    def setup_method(self):
        """Setup test fixtures."""
        self.mock_session = MagicMock()
        self.mock_session.next_turn = MagicMock(return_value="[Interviewer] Here's a question")

        self.rubric = {"competency_1": {"description": "Test"}}
        self.brief = {}
        self.fsm = InterviewerFSM(self.rubric, self.brief, self.mock_session)

    def test_all_states_have_cues(self):
        """Test that all states have associated cues."""
        for state in InterviewState:
            assert state in CUES
            assert isinstance(CUES[state], str)

    def test_cues_are_meaningful(self):
        """Test that cues contain helpful instructions."""
        for state, cue in CUES.items():
            assert "Open" in cue or "Closing" in cue or "Background" in cue or "Probe" in cue

    def test_cues_include_competency_probing(self):
        """Test that cues mention competency probing."""
        probing_cues = [cue for state, cue in CUES.items() if state == InterviewState.PROBING]
        assert len(probing_cues) > 0
        assert "competenc" in probing_cues[0].lower()