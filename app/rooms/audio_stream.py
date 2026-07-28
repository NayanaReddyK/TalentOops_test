"""Audio stream session buffer & VAD accumulator for room audio channels."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger("talentops.audio_stream")


class AudioSessionBuffer:
    """Maintains a continuous audio & transcript buffer for the current interview turn."""

    def __init__(self, room_id: str, silence_threshold_sec: float = 3.0) -> None:
        self.room_id = room_id
        self.silence_threshold_sec = silence_threshold_sec
        self.audio_chunks: list[bytes] = []
        self.accumulated_transcript: list[str] = []
        self.last_speech_time: float = 0.0
        self._lock = asyncio.Lock()

    async def append_chunk(self, chunk: bytes = b"", text_segment: str = "") -> None:
        """Append an audio chunk or finalized text segment to the turn buffer."""
        async with self._lock:
            if chunk:
                self.audio_chunks.append(chunk)
            if text_segment and text_segment.strip():
                self.accumulated_transcript.append(text_segment.strip())

    async def get_full_transcript(self) -> str:
        """Retrieve the concatenated transcript accumulated across natural pauses."""
        async with self._lock:
            return " ".join(self.accumulated_transcript)

    async def clear_turn_buffer(self) -> None:
        """Clear turn buffer after successful submission to Interviewer Agent."""
        async with self._lock:
            self.audio_chunks.clear()
            self.accumulated_transcript.clear()
            self.last_speech_time = 0.0


_room_buffers: dict[str, AudioSessionBuffer] = {}


def get_audio_session_buffer(room_id: str) -> AudioSessionBuffer:
    """Retrieve or create an AudioSessionBuffer for a given room."""
    if room_id not in _room_buffers:
        _room_buffers[room_id] = AudioSessionBuffer(room_id)
    return _room_buffers[room_id]
