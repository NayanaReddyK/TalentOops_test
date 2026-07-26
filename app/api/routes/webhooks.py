"""Vexa lifecycle webhooks (Task 4.1): media-stream ownership handover to the bridge."""
from fastapi import APIRouter

from app.services.audio_bridge import get_bridge, remove_bridge
from app.services.database import db

router = APIRouter()


@router.post("/webhooks/vexa")
async def vexa_webhook(payload: dict) -> dict:
    event = payload.get("event")
    meeting_id = payload.get("meeting_id", "")
    if event == "joined":
        get_bridge(meeting_id)  # stream ownership shifts to the session broker layer
    elif event == "left":
        remove_bridge(meeting_id)
    await db.insert("events", {"type": f"vexa.{event}", "meeting_id": meeting_id,
                               "payload": payload})
    return {"ok": True}
