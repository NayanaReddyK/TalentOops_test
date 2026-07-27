"""Room lifecycle webhooks: handles room session events from the audio bridge."""
from fastapi import APIRouter

from app.services.audio_bridge import get_bridge, remove_bridge
from app.services.database import db

router = APIRouter()


@router.post("/webhooks/room")
async def room_webhook(payload: dict) -> dict:
    """Handle room session lifecycle events from the audio bridge."""
    event      = payload.get("event")
    meeting_id = payload.get("meeting_id", "") or payload.get("room_id", "")
    if event == "joined":
        get_bridge(meeting_id)
    elif event == "left":
        remove_bridge(meeting_id)
    await db.insert("events", {
        "type":       f"room.{event}",
        "meeting_id": meeting_id,
        "payload":    payload,
    })
    return {"ok": True}
