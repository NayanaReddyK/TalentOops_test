"""TDD Unit Tests for 6-Stage Workflow State Machine & Upward Envelope Boundaries."""
import pytest
from app.graph.state import WorkflowStage, PipelineState
from app.graph.envelope import Envelope, make_envelope, EnvelopeValidationError
from app.agents.manager_agent import determine_next_stage


def test_workflow_stage_enum_values():
    assert WorkflowStage.APPLICATION_RECEIVED == "APPLICATION_RECEIVED"
    assert WorkflowStage.SCREENING == "SCREENING"
    assert WorkflowStage.SCHEDULING == "SCHEDULING"
    assert WorkflowStage.INTERVIEWING == "INTERVIEWING"
    assert WorkflowStage.EVALUATION == "EVALUATION"
    assert WorkflowStage.HR_DEBRIEF == "HR_DEBRIEF"
    assert WorkflowStage.COMPLETED == "COMPLETED"


def test_determine_next_stage_sequence():
    stage, target = determine_next_stage(WorkflowStage.APPLICATION_RECEIVED, [])
    assert stage == WorkflowStage.SCREENING
    assert target == "sourcing"

    stage, target = determine_next_stage(WorkflowStage.SCREENING, ["sourcing"])
    assert stage == WorkflowStage.SCREENING
    assert target == "screening"

    stage, target = determine_next_stage(WorkflowStage.SCREENING, ["sourcing", "screening"])
    assert stage == WorkflowStage.SCHEDULING
    assert target == "scheduling"

    stage, target = determine_next_stage(WorkflowStage.SCHEDULING, ["sourcing", "screening", "scheduling"])
    assert stage == WorkflowStage.INTERVIEWING
    assert target == "interviewer"

    stage, target = determine_next_stage(WorkflowStage.INTERVIEWING, ["sourcing", "screening", "scheduling", "interviewer"])
    assert stage == WorkflowStage.EVALUATION
    assert target == "reporting"

    stage, target = determine_next_stage(WorkflowStage.EVALUATION, ["sourcing", "screening", "scheduling", "interviewer", "reporting"])
    assert stage == WorkflowStage.HR_DEBRIEF
    assert target == "FINISH"


def test_upward_envelope_recipient_validation():
    env = make_envelope(sender="screening", recipient="manager", kind="result", body={"rankings": [1, 2]})
    assert env["sender"] == "screening"
    assert env["recipient"] == "manager"

    with pytest.raises(EnvelopeValidationError):
        # Direct subagent reporting to HR violates boundary rule
        make_envelope(sender="screening", recipient="HR", kind="result", body={})
