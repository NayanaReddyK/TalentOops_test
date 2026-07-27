"""FastAPI router for Interview Room REST endpoints.

Routes
──────
POST /rooms/create           — create a room, get back room_id + room_url
GET  /rooms/{room_id}        — fetch current room status
POST /rooms/{room_id}/end    — close a room (HR or system)
WS   /ws/room/{room_id}      — WebSocket session (mounted in main.py)
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket

from app.rooms.models import CreateRoomRequest, CreateRoomResponse, RoomStatus
from app.rooms.room_manager import room_manager
from app.rooms.signaling import room_ws_handler

logger = logging.getLogger("talentops.rooms_router")

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("/create", response_model=CreateRoomResponse)
async def create_room(req: CreateRoomRequest) -> dict[str, Any]:
    """Create a new self-hosted interview room and return its URL."""
    room = await room_manager.create_room(
        candidate_id=req.candidate_id,
        interview_id=req.interview_id,
        metadata={"slot_iso": req.slot_iso, **(req.metadata or {})},
    )
    return {
        "room_id":  room.room_id,
        "room_url": room.room_url,
        "status":   room.status,
    }


@router.get("/{room_id}")
async def get_room(room_id: str) -> dict[str, Any]:
    """Return current room metadata and status."""
    room = room_manager.get_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail=f"Room {room_id!r} not found")
    return room.model_dump()


@router.post("/{room_id}/end")
async def end_room(room_id: str) -> dict[str, Any]:
    """Close a room session (idempotent)."""
    room = room_manager.get_room(room_id)
    if room is None:
        # Already closed or never existed — treat as success
        return {"status": "already_closed", "room_id": room_id}
    await room_manager.close_room(room_id)
    return {"status": "closed", "room_id": room_id}


# WebSocket endpoint — registered separately in main.py so FastAPI can handle
# the WebSocket upgrade path outside the router prefix.
async def ws_room_endpoint(websocket: WebSocket, room_id: str) -> None:
    await room_ws_handler(websocket, room_id)
