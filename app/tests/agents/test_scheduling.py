"""TDD unit tests for Phase 2 Calendar, Scheduling & Google Meet Invitation module."""
import pytest
from app.agents.calendar_client import MockCalendarClient, get_calendar_client
from app.agents.scheduling import run_scheduling
from app.agents.communication import send_invite, get_email_client
from app.graph.nodes import scheduling_node


def test_mock_calendar_client_returns_meet_link():
    client = MockCalendarClient()
    slots = client.find_slots(duration_min=45, count=2)
    assert len(slots) == 2
    booking = client.book(slots[0], "alex@example.com", "Test Interview")
    assert booking["status"] == "confirmed"
    assert "meet_link" in booking
    assert "meet.google.com" in booking["meet_link"]


def test_run_scheduling_with_meet_link():
    res = run_scheduling("run-101", top_candidate="Alex Chen", candidate_email="alex.chen@example.com")
    assert res["status"] == "booked"
    assert "booking" in res
    assert "meet_link" in res["booking"]
    assert res["booking"]["attendee"] == "alex.chen@example.com"


def test_send_invite_includes_meet_link():
    email_client = get_email_client()
    initial_count = len(email_client.outbox)
    res = send_invite("run-102", "Priya Rao", "2026-07-26T14:00:00Z", "https://meet.google.com/test-meet-123", "priya@example.com")
    assert res["kind"] == "invite"
    assert res["to"] == "priya@example.com"
    assert len(email_client.outbox) == initial_count + 1
    last_msg = email_client.outbox[-1]
    assert "https://meet.google.com/test-meet-123" in last_msg.body


def test_scheduling_node_emits_stage_and_envelope():
    state = {
        "run_id": "run-103",
        "top_candidate": "Priya Rao",
        "completed": ["screening"],
        "messages": [],
    }
    result_state = scheduling_node(state)
    assert result_state["stage"] == "INTERVIEWING"
    assert "scheduling" in result_state["completed"]
    assert len(result_state["messages"]) == 1
    env = result_state["messages"][0]
    assert env["sender"] == "scheduling"
    assert env["recipient"] == "manager"
    assert env["body"]["booking"]["meet_link"] != ""
