"""Manager Agent escalation rules + pipeline decisions (Task 6.6)."""
from app.services.database import db
from app.services.email_handler import send_email

VALID_REASONS = {"low_confidence", "double_conflict", "no_qualified_candidates",
                 "review_limit_exceeded", "delivery_failure",
                 "protected_attribute_flag", "reschedule_required"}


class ManagerAgent:
    def __init__(self, role_id: str, user_email: str = "manager@example.com") -> None:
        self.role_id = role_id
        self.user_email = user_email

    async def escalate(self, reason: str, details_ref: str | None = None,
                       candidate_id: str | None = None) -> dict:
        if reason not in VALID_REASONS:
            raise ValueError(f"unknown escalation reason {reason!r}")
        payload = {
            "type": "escalation",
            "reason": reason,
            "role_id": self.role_id,
            "details_ref": details_ref,
            "candidate_id": candidate_id,
        }
        event = await db.insert("events", payload)
        await send_email(self.user_email, f"[TalentOps escalation] {reason}",
                         f"Escalation {reason} for role {self.role_id} "
                         f"(candidate: {candidate_id or 'n/a'}, ref: {details_ref or 'n/a'}).")
        if isinstance(event, dict):
            res = dict(payload)
            res.update(event)
            return res
        return payload

    async def on_interviewer_result(self, result: dict) -> dict | None:
        if result.get("needs_human_review"):
            return await self.escalate("low_confidence",
                                       details_ref=result.get("transcript_ref"),
                                       candidate_id=result.get("candidate_id"))
        return None

    async def on_scheduling(self, status: str, conflict_count: int,
                            candidate_id: str | None = None) -> dict | None:
        if conflict_count >= 2 or status == "rejected":
            return await self.escalate("double_conflict", candidate_id=candidate_id)
        return None

    async def on_sourcing_cycle(self, cycles: int, qualified_count: int) -> dict | None:
        if qualified_count == 0 and cycles >= 2:
            return await self.escalate("no_qualified_candidates")
        return None

    async def decide(self, scorecard_result: dict) -> str:
        card = scorecard_result["scorecard"]
        candidate_id = scorecard_result.get("candidate_id")
        if card.get("needs_human_review"):
            await self.escalate("low_confidence", candidate_id=candidate_id)
            return "hold"
        decision = "invite" if card.get("overall_fit", 0.0) >= 0.7 else "reject"
        await send_email(self.user_email, f"[TalentOps decision] {decision}",
                         f"Candidate {candidate_id}: {decision} "
                         f"(fit {card.get('overall_fit'):.2f}).")
        return decision

    async def with_failure_handling(self, coro_fn, *args):
        # covers loss of API connection / Vexa session drops (Task 6.6)
        try:
            return await coro_fn(*args)
        except Exception as e:
            await db.insert("events", {"type": "task.error", "role_id": self.role_id,
                                       "error": str(e)})
            raise


def determine_next_stage(current_stage: str | None, completed: list[str]) -> tuple[str, str]:
    """Determine the next target WorkflowStage and target subagent node."""
    from app.graph.state import WorkflowStage

    if not current_stage or current_stage == WorkflowStage.APPLICATION_RECEIVED:
        return WorkflowStage.SCREENING, "sourcing"

    if current_stage == WorkflowStage.SCREENING:
        if "sourcing" not in completed:
            return WorkflowStage.SCREENING, "sourcing"
        if "screening" not in completed:
            return WorkflowStage.SCREENING, "screening"
        return WorkflowStage.SCHEDULING, "scheduling"

    if current_stage == WorkflowStage.SCHEDULING:
        if "scheduling" not in completed:
            return WorkflowStage.SCHEDULING, "scheduling"
        return WorkflowStage.INTERVIEWING, "interviewer"

    if current_stage == WorkflowStage.INTERVIEWING:
        if "interviewer" not in completed:
            return WorkflowStage.INTERVIEWING, "interviewer"
        return WorkflowStage.EVALUATION, "reporting"

    if current_stage == WorkflowStage.EVALUATION:
        if "reporting" not in completed:
            return WorkflowStage.EVALUATION, "reporting"
        return WorkflowStage.HR_DEBRIEF, "FINISH"

    if current_stage == WorkflowStage.HR_DEBRIEF:
        return WorkflowStage.COMPLETED, "FINISH"

    return WorkflowStage.COMPLETED, "FINISH"
