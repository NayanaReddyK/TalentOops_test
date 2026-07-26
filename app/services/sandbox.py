"""Pre-Flight Sandbox (Task 4.4): 2-min non-graded calibration + telemetry gate."""
from app.config import settings
from app.services.database import db

SMALL_TALK = [
    "Hi! Before we start, this is a quick non-graded mic and connection check.",
    "How's your audio on your end? Feel free to say a sentence or two.",
    "Great — any questions about how the interview works before we begin?",
]

BOUNDARY_ANNOUNCEMENT = "the official interview will now begin"


def telemetry_gate(rtt_ms: float, jitter_ms: float) -> bool:
    return (rtt_ms <= settings.TELEMETRY_MAX_RTT_MS
            and jitter_ms <= settings.TELEMETRY_MAX_JITTER_MS)


class PreFlightSandbox:
    def __init__(self, session, interview_id: str, duration_sec: int = 120) -> None:
        self.session = session  # duck-typed voice session; sandbox adds no new speaker
        self.interview_id = interview_id
        self.duration_sec = min(duration_sec, settings.SANDBOX_MAX_SEC)

    async def run(self, telemetry: dict | None = None) -> dict:
        # Grading isolation: sandbox dialogue stays in this return value only —
        # it must never reach the interview transcript or the scoring path.
        dialogue = list(SMALL_TALK)
        t = telemetry or {"rtt_ms": 80.0, "jitter_ms": 10.0, "audio_level": 0.8}
        passed = telemetry_gate(t["rtt_ms"], t["jitter_ms"])
        row = await db.insert("calibration", {
            "interview_id": self.interview_id,
            "rtt_ms": t["rtt_ms"],
            "jitter_ms": t["jitter_ms"],
            "audio_level": t.get("audio_level", 0.0),
            "passed": passed,
        })
        if not passed:
            return {"passed": False, "calibration_id": row["id"],
                    "sandbox_dialogue": dialogue,
                    "escalation": {"reason": "reschedule_required",
                                   "details_ref": row["id"], "candidate_id": None}}
        return {"passed": True, "calibration_id": row["id"],
                "sandbox_dialogue": dialogue,
                "boundary_announcement": BOUNDARY_ANNOUNCEMENT}
