"""Unit tests for AudioSessionBuffer and turn-level STT accumulation."""
from __future__ import annotations

import pytest
from app.rooms.audio_stream import AudioSessionBuffer, get_audio_session_buffer


@pytest.mark.asyncio
async def test_audio_session_buffer_accumulation():
    """Buffer should accumulate multi-phrase speech segments across pauses."""
    buf = AudioSessionBuffer(room_id="test-room-vad", silence_threshold_sec=3.0)

    # Candidate speaks sentence 1
    await buf.append_chunk(chunk=b"audio_chunk_1", text_segment="I have built legal document processing microservices")
    # Candidate pauses brief 1s, then speaks sentence 2
    await buf.append_chunk(chunk=b"audio_chunk_2", text_segment="using Python, FastAPI, and PostgreSQL.")
    # Candidate speaks sentence 3
    await buf.append_chunk(chunk=b"audio_chunk_3", text_segment="We handled high concurrency with AsyncIO.")

    full_transcript = await buf.get_full_transcript()

    assert "legal document processing" in full_transcript
    assert "FastAPI" in full_transcript
    assert "AsyncIO" in full_transcript
    assert len(buf.audio_chunks) == 3


@pytest.mark.asyncio
async def test_audio_session_buffer_clear_turn():
    """Clearing turn buffer resets audio chunks and transcript."""
    buf = AudioSessionBuffer(room_id="test-room-clear", silence_threshold_sec=3.0)
    await buf.append_chunk(chunk=b"chunk", text_segment="First phrase")

    assert len(await buf.get_full_transcript()) > 0
    await buf.clear_turn_buffer()
    assert len(await buf.get_full_transcript()) == 0
    assert len(buf.audio_chunks) == 0


def test_get_audio_session_buffer_singleton():
    """get_audio_session_buffer should retrieve or create a per-room singleton buffer."""
    buf1 = get_audio_session_buffer("room-101")
    buf2 = get_audio_session_buffer("room-101")
    buf3 = get_audio_session_buffer("room-102")

    assert buf1 is buf2
    assert buf1 is not buf3
