"""Speech Engine (STT & TTS) with low-latency non-blocking async execution."""
from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any

logger = logging.getLogger("talentops.speech_engine")


class STTService:
    """Async Speech-to-Text service for candidate audio transcription."""

    def __init__(self, provider: str = "mock"):
        self.provider = provider

    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes to text string (non-blocking async)."""
        if not audio_bytes:
            return ""

        # Non-blocking async execution
        try:
            return await asyncio.to_thread(self._transcribe_sync, audio_bytes)
        except Exception as e:
            logger.error("STT transcription error: %s", e)
            return "Candidate response transcript unavailable"

    def _transcribe_sync(self, audio_bytes: bytes) -> str:
        # If text string was passed in raw bytes format, decode directly
        try:
            decoded = audio_bytes.decode("utf-8")
            if decoded.strip() and not decoded.startswith(b"\x00"[:1]):
                return decoded.strip()
        except Exception:
            pass

        # Synthetic/mock STT fallback for test audio frames
        length_hint = len(audio_bytes)
        if length_hint > 100:
            return f"Transcribed speech from audio stream ({length_hint} bytes)"
        return "Spoken response"


class TTSService:
    """Async Text-to-Speech service for generating spoken audio questions."""

    def __init__(self, provider: str = "mock"):
        self.provider = provider

    async def synthesize_speech(self, text: str) -> bytes:
        """Synthesize text string into spoken audio frame bytes (non-blocking async)."""
        if not text:
            return b""

        try:
            return await asyncio.to_thread(self._synthesize_sync, text)
        except Exception as e:
            logger.error("TTS synthesis error: %s", e)
            return text.encode("utf-8")

    def _synthesize_sync(self, text: str) -> bytes:
        # Synthetic audio frame payload (encoded header + text)
        header = b"AUDIO_FRAME_PCM_16KHZ:"
        return header + text.encode("utf-8")

    async def synthesize_speech_b64(self, text: str) -> str:
        audio_bytes = await self.synthesize_speech(text)
        return base64.b64encode(audio_bytes).decode("utf-8")


def handle_barge_in(session_id: str) -> dict[str, Any]:
    """Handle candidate interruption (barge-in) during active agent speech playback."""
    logger.info("Barge-in / interruption detected for session: %s", session_id)
    return {"session_id": session_id, "interrupted": True, "action": "stop_tts_playback"}
