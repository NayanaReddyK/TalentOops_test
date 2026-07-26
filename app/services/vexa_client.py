"""Vexa Google Meet bot client (Task 4.1): join/leave lifecycle + status."""
import uuid

import httpx

from app.config import settings
from app.services.database import db


class VexaClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or settings.VEXA_API_BASE

    def _get_client(self) -> httpx.AsyncClient:
        headers = {}
        if settings.VEXA_API_KEY:
            headers["Authorization"] = f"Bearer {settings.VEXA_API_KEY}"
            headers["x-api-key"] = settings.VEXA_API_KEY
        return httpx.AsyncClient(timeout=30, headers=headers)

    async def join_meeting(self, meet_url: str, bot_name: str, voice_context: str, interview_id: str) -> dict:
        async with self._get_client() as client:
            r = await client.post(f"{self.base_url}/bots", json={
                "meeting_url": meet_url, 
                "bot_name": bot_name, 
                "voice_context": voice_context, 
                "platform": "google_meet",
                "transcription_service_url": f"ws://host.docker.internal:8000/ws/audio/{interview_id}",
                "transcription_service_token": "talentops-token",
                "transcribe_enabled": False
            })
            if r.status_code == 409:
                # Bot is already in the meeting, treat as success!
                return {"meeting_id": "existing-session", "status": "already_joined"}
            r.raise_for_status()
            return r.json()

    async def leave_meeting(self, meeting_id: str) -> dict:
        async with self._get_client() as client:
            r = await client.delete(f"{self.base_url}/bots/{meeting_id}")
            r.raise_for_status()
            return r.json()

    async def get_status(self, meeting_id: str) -> dict:
        async with self._get_client() as client:
            r = await client.get(f"{self.base_url}/bots/{meeting_id}")
            r.raise_for_status()
            return r.json()


def get_vexa_client() -> VexaClient:
    return VexaClient()
