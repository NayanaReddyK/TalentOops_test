"""WebSocket signaling handler for TalentOops self-hosted Interview Rooms.

Each candidate and HR client connects to:
    ws://localhost:8000/ws/room/{room_id}

Frame protocol (JSON):
    Client → Server:  {"type": "<SignalType>", "data": {...}}
    Server → Client:  {"type": "<SignalType>", "data": {...}}

Agent pipeline execution order (inside this handler):
    1. Consent Agent  — discloses recording policy, collects consent
    2. Interviewer FSM — runs structured interview turns
    3. Evaluator Agent — scores transcript concurrently, streams updates
    4. Session End     — emits final scorecard + transitions room to COMPLETED
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from app.rooms.models import RoomStatus, SignalType
from app.rooms.room_manager import room_manager
from app.supabase_client import log_event

logger = logging.getLogger("talentops.room_signaling")


# ─── helpers ──────────────────────────────────────────────────────────────────

def _frame(signal_type: SignalType, data: dict[str, Any]) -> dict[str, Any]:
    return {"type": signal_type.value, "data": data}


async def _safe_send(ws: WebSocket, payload: dict[str, Any]) -> None:
    try:
        await ws.send_json(payload)
    except Exception as exc:
        logger.warning("send_json failed: %s", exc)


# ─── agent pipeline ────────────────────────────────────────────────────────────

async def _run_agent_pipeline(
    room_id: str,
    interview_id: str,
    candidate_id: str,
    role_id: str,
    consent_response: str,
    candidate_turns: list[str],
    run_id: str,
) -> dict[str, Any]:
    """Execute Consent → Interview → Evaluator inside the room session."""
    from app.agents.consent_agent import ConsentAgent
    from app.agents.evaluator_agent import EvaluatorAgent
    from app.agents.interviewer_fsm import InterviewerFSM
    from app.services.database import db

    # ── 1. Consent Agent ────────────────────────────────────────────────────
    consent_agent = ConsentAgent()
    consent_result = await consent_agent.process_response(
        candidate_id=candidate_id,
        response_text=consent_response,
        room_id=room_id,
        run_id=run_id,
    )

    await room_manager.broadcast(room_id, _frame(SignalType.AGENT_MESSAGE, {
        "agent": "consent",
        "consent_granted": consent_result["consent_granted"],
        "reasoning": consent_result["reasoning"],
    }))

    if not consent_result["consent_granted"]:
        return {"status": "consent_denied", "consent_result": consent_result}

    # Mark room as active now that consent is granted
    await room_manager.update_status(room_id, RoomStatus.ACTIVE)

    # ── 2. Interviewer FSM ──────────────────────────────────────────────────
    rubrics = await db.query("rubrics", run_id=run_id)
    rubric = rubrics[0] if rubrics else {
        "standard": f"Role ({role_id})",
        "competencies": [{"competency_id": "core_skills", "keywords": ["python", "backend"]}],
    }

    class _AsyncSession:
        async def inject_context(self, text: str) -> None: pass
        async def next_turn(self, text: str) -> str:
            return f"Tell me more about: {text[:80]}"

    fsm = InterviewerFSM(
        rubric=rubric,
        brief={"candidate_name": candidate_id},
        session=_AsyncSession(),
    )

    # Stream each turn back to the room as it progresses
    for i, turn_text in enumerate(candidate_turns or ["I have backend engineering experience."]):
        await room_manager.broadcast(room_id, _frame(SignalType.INTERVIEW_TURN, {
            "turn_number": i + 1,
            "speaker": "candidate",
            "text": turn_text,
        }))
        await asyncio.sleep(0.05)  # Yield event loop

    fsm_result = await fsm.run_interview(
        candidate_turns or ["I have backend engineering experience."],
        transcript_ref=interview_id,
    )

    # ── 3. Evaluator Agent ──────────────────────────────────────────────────
    transcript_formatted = [
        {"speaker": "interviewer", "text": "Please tell me about your experience."},
        *[{"speaker": "candidate", "text": t} for t in (candidate_turns or [])],
    ]

    evaluator = EvaluatorAgent(run_id=run_id)
    scorecard_result = await evaluator.evaluate_transcript(
        interview_id=interview_id,
        candidate_id=candidate_id,
        rubric=rubric,
        transcript_turns=transcript_formatted,
    )

    # Broadcast partial eval update
    await room_manager.broadcast(room_id, _frame(SignalType.EVAL_UPDATE, {
        "scorecard": scorecard_result.get("scorecard", {}),
        "final_recommendation": scorecard_result.get("final_recommendation", {}),
        "behavioral_metrics": scorecard_result.get("behavioral_metrics", {}),
    }))

    log_event(
        run_id=run_id,
        source="room_signaling",
        event_type="interview_completed",
        payload={
            "room_id": room_id,
            "interview_id": interview_id,
            "scorecard_id": scorecard_result.get("scorecard_id"),
        },
    )

    return {
        "status": "completed",
        "fsm_summary": fsm_result,
        "scorecard": scorecard_result,
    }


# ─── WebSocket handler ─────────────────────────────────────────────────────────

async def room_ws_handler(websocket: WebSocket, room_id: str) -> None:
    """Main WebSocket endpoint handler for a room session."""
    await websocket.accept()

    # Verify room exists
    room = room_manager.get_room(room_id)
    if room is None:
        await _safe_send(websocket, _frame(SignalType.ERROR, {
            "message": f"Room {room_id!r} does not exist or has expired."
        }))
        await websocket.close(code=4004)
        return

    # Register this client
    session = await room_manager.join_room(room_id, websocket)

    # Announce join
    await _safe_send(websocket, _frame(SignalType.ROOM_JOINED, {
        "room_id":      room_id,
        "room_url":     room.room_url,
        "candidate_id": room.candidate_id,
        "interview_id": room.interview_id,
        "status":       room.status.value,
    }))

    # Send consent disclosure
    from app.agents.consent_agent import ConsentAgent
    disclosure = ConsentAgent().get_disclosure_script(room.candidate_id)
    await _safe_send(websocket, _frame(SignalType.CONSENT_ASK, {"text": disclosure}))

    # State accumulators
    consent_response: str = ""
    candidate_turns:  list[str] = []
    pipeline_started  = False
    run_id            = f"run-room-{room_id[:8]}"

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await _safe_send(websocket, _frame(SignalType.ERROR, {"message": "Invalid JSON frame"}))
                continue

            msg_type = msg.get("type", "")
            data     = msg.get("data", {})

            # ── WebRTC signaling passthrough ──────────────────────────────
            if msg_type in (SignalType.OFFER.value, SignalType.ANSWER.value, SignalType.ICE_CANDIDATE.value):
                # Relay to all other clients in the room (simple P2P relay)
                await room_manager.broadcast(room_id, {
                    "type": msg_type,
                    "data": data,
                    "from": "peer",
                })

            # ── Consent response ──────────────────────────────────────────
            elif msg_type == SignalType.CONSENT_RESPONSE.value:
                consent_response = data.get("text", "")
                if not pipeline_started:
                    pipeline_started = True
                    role_id = room.metadata.get("role_id", "r-default")

                    # Run pipeline as a background asyncio task
                    async def _run_pipeline() -> None:
                        result = await _run_agent_pipeline(
                            room_id=room_id,
                            interview_id=room.interview_id,
                            candidate_id=room.candidate_id,
                            role_id=role_id,
                            consent_response=consent_response,
                            candidate_turns=candidate_turns,
                            run_id=run_id,
                        )
                        if result.get("status") == "completed":
                            try:
                                from app.agents.reporting import run_reporting
                                scorecard = result.get("scorecard", {})
                                needs_review = scorecard.get("scorecard", {}).get("needs_human_review", False)
                                state = {
                                    "shortlist": [{"ref_id": room.candidate_id}],
                                    "top_candidate": room.candidate_id,
                                    "results": {"interview": scorecard},
                                    "needs_review": needs_review,
                                    "goal": "Candidate Interview Outcomes"
                                }
                                reporting_result = await asyncio.to_thread(run_reporting, run_id, state)
                                
                                log_event(
                                    run_id=run_id,
                                    source="room_signaling",
                                    event_type="reporting_completed",
                                    payload=reporting_result
                                )
                                result["reporting_result"] = reporting_result
                            except Exception as rep_exc:
                                logger.error("Reporting failed for room %s: %s", room_id, rep_exc)
                                
                        await room_manager.broadcast(room_id, _frame(SignalType.SESSION_END, result))
                        await room_manager.close_room(room_id)

                    task = asyncio.create_task(_run_pipeline())
                    session.agent_task = task

            # ── Candidate answer turn ─────────────────────────────────────
            elif msg_type == SignalType.INTERVIEW_TURN.value:
                candidate_turns.append(data.get("text", ""))

            # ── Client-initiated session end ──────────────────────────────
            elif msg_type == SignalType.SESSION_END.value:
                await room_manager.close_room(room_id)
                break

    except WebSocketDisconnect:
        logger.info("Client disconnected from room %s", room_id)
    except Exception as exc:
        logger.error("Room WS error (%s): %s", room_id, exc)
        await _safe_send(websocket, _frame(SignalType.ERROR, {"message": str(exc)}))
    finally:
        await room_manager.leave_room(room_id, websocket)
