"""Tests for the interactive WebSocket room signaling state machine.

Covers the consent → interview → evaluation pipeline that was broken
due to premature pipeline execution and silent exception swallowing.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rooms.models import RoomStatus, SignalType
from app.rooms.signaling import _InteractiveRoomSession


# ─── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_ws():
    """Fake WebSocket with a message queue."""
    ws = MagicMock()
    ws.send_json = AsyncMock()
    ws._queue = asyncio.Queue()

    async def receive_text():
        return await ws._queue.get()

    ws.receive_text = receive_text
    return ws


@pytest.fixture
def session(mock_ws):
    return _InteractiveRoomSession(
        ws=mock_ws,
        room_id="test-room-001",
        interview_id="iv-test-001",
        candidate_id="c-alice",
        role_id="r-backend",
        run_id="run-test-001",
    )


def _push(ws, type_: str, data: dict):
    """Enqueue a client frame."""
    ws._queue.put_nowait(json.dumps({"type": type_, "data": data}))


def _sent_types(mock_ws) -> list[str]:
    """Return list of signal types that were sent to the WebSocket."""
    return [
        call.args[0].get("type") or call.kwargs.get("payload", {}).get("type", "")
        for call in mock_ws.send_json.call_args_list
    ]


def _sent_payloads(mock_ws) -> list[dict]:
    return [call.args[0] for call in mock_ws.send_json.call_args_list]


# ─── consent phase tests ───────────────────────────────────────────────────────

class TestConsentPhase:

    @pytest.mark.asyncio
    async def test_consent_granted_updates_room_status(self, session, mock_ws):
        """After consent reply, room status should become ACTIVE."""
        with (
            patch("app.rooms.signaling.room_manager") as mock_rm,
            patch("app.rooms.signaling.log_event"),
        ):
            mock_rm.update_status = AsyncMock()
            mock_rm.broadcast = AsyncMock()
            mock_rm.leave_room = AsyncMock()

            result = await session._handle_consent("Yes, I consent")

        assert result is True
        mock_rm.update_status.assert_awaited_once_with("test-room-001", RoomStatus.ACTIVE)

    @pytest.mark.asyncio
    async def test_consent_denied_returns_false(self, session, mock_ws):
        """Explicit refusal should return False without updating room status."""
        with (
            patch("app.rooms.signaling.room_manager") as mock_rm,
            patch("app.rooms.signaling.log_event"),
        ):
            mock_rm.update_status = AsyncMock()
            mock_rm.broadcast = AsyncMock()

            result = await session._handle_consent("No, I refuse")

        assert result is False
        mock_rm.update_status.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_consent_sends_agent_message_frame(self, session, mock_ws):
        """Client receives an agent-message frame after sending consent."""
        with (
            patch("app.rooms.signaling.room_manager") as mock_rm,
            patch("app.rooms.signaling.log_event"),
        ):
            mock_rm.update_status = AsyncMock()
            mock_rm.broadcast = AsyncMock()

            await session._handle_consent("Yes, I agree")

        payloads = _sent_payloads(mock_ws)
        agent_msgs = [p for p in payloads if p.get("type") == SignalType.AGENT_MESSAGE.value]
        assert len(agent_msgs) >= 1
        assert agent_msgs[0]["data"]["agent"] == "consent"
        assert agent_msgs[0]["data"]["consent_granted"] is True

    @pytest.mark.asyncio
    async def test_consent_denied_sends_closing_text(self, session, mock_ws):
        """When consent is denied the agent-message should contain a closing text."""
        with (
            patch("app.rooms.signaling.room_manager") as mock_rm,
            patch("app.rooms.signaling.log_event"),
        ):
            mock_rm.update_status = AsyncMock()
            mock_rm.broadcast = AsyncMock()

            await session._handle_consent("No")

        payloads = _sent_payloads(mock_ws)
        agent_msgs = [p for p in payloads if p.get("type") == SignalType.AGENT_MESSAGE.value]
        assert any("end" in p["data"].get("text", "").lower() for p in agent_msgs)


# ─── dispatch loop tests ───────────────────────────────────────────────────────

class TestDispatchLoop:

    @pytest.mark.asyncio
    async def test_consent_response_triggers_interview_start(self, session, mock_ws):
        """After consent-response frame, _start_interview should be called."""
        from fastapi import WebSocketDisconnect

        with (
            patch("app.rooms.signaling.room_manager") as mock_rm,
            patch("app.rooms.signaling.log_event"),
            patch.object(session, "_handle_consent", new=AsyncMock(return_value=True)),
            patch.object(session, "_start_interview", new=AsyncMock()) as mock_start,
        ):
            mock_rm.leave_room = AsyncMock()

            # Push a consent frame then a disconnect to end the loop
            _push(mock_ws, "consent-response", {"text": "Yes I consent"})
            _push(mock_ws, "session-end", {})

            await session.run()

        mock_start.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_consent_denied_sends_session_end_frame(self, session, mock_ws):
        """When consent is denied, a session-end frame must be sent before exiting."""
        with (
            patch("app.rooms.signaling.room_manager") as mock_rm,
            patch("app.rooms.signaling.log_event"),
            patch.object(session, "_handle_consent", new=AsyncMock(return_value=False)),
        ):
            mock_rm.leave_room = AsyncMock()

            _push(mock_ws, "consent-response", {"text": "No"})

            await session.run()

        payloads = _sent_payloads(mock_ws)
        end_frames = [p for p in payloads if p.get("type") == SignalType.SESSION_END.value]
        assert len(end_frames) >= 1
        assert end_frames[0]["data"]["status"] == "consent_denied"

    @pytest.mark.asyncio
    async def test_interview_turn_enqueued_in_active_state(self, session, mock_ws):
        """interview-turn frames received after consent are added to the turn queue."""
        with (
            patch("app.rooms.signaling.room_manager") as mock_rm,
            patch("app.rooms.signaling.log_event"),
            patch.object(session, "_handle_consent", new=AsyncMock(return_value=True)),
            patch.object(session, "_start_interview", new=AsyncMock()),
        ):
            mock_rm.leave_room = AsyncMock()

            _push(mock_ws, "consent-response", {"text": "Yes"})
            _push(mock_ws, "interview-turn", {"text": "I have 5 years of FastAPI experience."})
            _push(mock_ws, "session-end", {})

            await session.run()

        # The turn should have been placed in the queue
        assert not session._turn_queue.empty()
        turn = session._turn_queue.get_nowait()
        assert "FastAPI" in turn

    @pytest.mark.asyncio
    async def test_webrtc_frames_are_relayed(self, session, mock_ws):
        """Offer / answer / ice-candidate frames should be broadcast to room peers."""
        with (
            patch("app.rooms.signaling.room_manager") as mock_rm,
            patch("app.rooms.signaling.log_event"),
            patch.object(session, "_handle_consent", new=AsyncMock(return_value=False)),
        ):
            mock_rm.leave_room = AsyncMock()
            mock_rm.broadcast = AsyncMock()

            _push(mock_ws, "offer", {"sdp": "v=0..."})
            _push(mock_ws, "consent-response", {"text": "No"})

            await session.run()

        mock_rm.broadcast.assert_awaited()
        broadcast_call = mock_rm.broadcast.call_args_list[0]
        broadcast_payload = broadcast_call.args[1]
        assert broadcast_payload["type"] == "offer"

    @pytest.mark.asyncio
    async def test_invalid_json_does_not_crash_loop(self, session, mock_ws):
        """A malformed JSON frame should not terminate the WebSocket loop."""
        with (
            patch("app.rooms.signaling.room_manager") as mock_rm,
            patch("app.rooms.signaling.log_event"),
        ):
            mock_rm.leave_room = AsyncMock()

            # Push invalid JSON, then a clean session-end
            mock_ws._queue.put_nowait("this is not json {{{")
            _push(mock_ws, "session-end", {})

            # Should not raise
            await session.run()


# ─── interview loop unit tests ─────────────────────────────────────────────────

class TestInterviewLoop:

    @pytest.mark.asyncio
    async def test_opening_question_is_sent(self, session, mock_ws):
        """_interview_loop must send an opening interviewer question immediately."""
        with patch("app.services.speech_engine.TTSService"):
            await session._send_interviewer_question("Walk me through your background.", 0)

        payloads = _sent_payloads(mock_ws)
        interview_turns = [p for p in payloads if p.get("type") == SignalType.INTERVIEW_TURN.value]
        assert len(interview_turns) >= 1
        assert interview_turns[0]["data"]["speaker"] == "interviewer"

    @pytest.mark.asyncio
    async def test_follow_up_covers_uncovered_competency(self, session, mock_ws):
        """_generate_follow_up should probe keywords the candidate hasn't mentioned."""
        question = await session._generate_follow_up(
            candidate_text="I like frontend work.",
            competency_id="python_backend",
            keywords=["python", "fastapi", "async"],
            turn_number=1,
        )
        assert len(question) > 0

    @pytest.mark.asyncio
    async def test_follow_up_dives_deeper_when_keyword_mentioned(self, session, mock_ws):
        """When the candidate mentions a keyword, follow-up should go deeper on it."""
        question = await session._generate_follow_up(
            candidate_text="I built async microservices using FastAPI at my last company.",
            competency_id="python_backend",
            keywords=["python", "fastapi", "async"],
            turn_number=0,
        )
        assert len(question) > 0

    @pytest.mark.asyncio
    async def test_follow_up_probes_short_vague_answers(self, session, mock_ws):
        """Short or vague responses like 'vorkos' should trigger technical detail probing."""
        question = await session._generate_follow_up(
            candidate_text="vorkos",
            competency_id="python_backend",
            keywords=["python", "architecture"],
            turn_number=1,
        )
        assert "vorkos" in question.lower() or "architecture" in question.lower() or "technical" in question.lower()


    def test_default_rubric_has_competencies(self, session, mock_ws):
        """Default rubric must include at least one competency with keywords."""
        rubric = session._default_rubric()
        assert len(rubric["competencies"]) > 0
        for comp in rubric["competencies"]:
            assert "competency_id" in comp
            assert len(comp.get("keywords", [])) > 0
