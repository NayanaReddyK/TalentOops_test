"""LangGraph supervisor graph wiring the Manager to its sub-agents."""
from __future__ import annotations

import uuid

from langgraph.graph import END, START, StateGraph

from app.graph.nodes import WORKER_NODES, manager_node
from app.graph.state import SUB_AGENTS, PipelineState
from app.supabase_client import log_event


def build_graph():
    """Construct and compile the supervisor StateGraph."""
    graph = StateGraph(PipelineState)

    graph.add_node("manager", manager_node)
    for name, node in WORKER_NODES.items():
        graph.add_node(name, node)

    graph.add_edge(START, "manager")

    route_map = {name: name for name in SUB_AGENTS}
    route_map["FINISH"] = END
    graph.add_conditional_edges("manager", lambda s: s["next"], route_map)

    for name in SUB_AGENTS:
        graph.add_edge(name, "manager")

    return graph.compile()


SUPERVISOR = build_graph()


async def run_pipeline(goal: str, standard: str | None = None, corpus: list[dict] | None = None) -> dict:
    """Execute one full pipeline run and return the final state."""
    run_id = str(uuid.uuid4())
    log_event(run_id, source="manager", event_type="run_started",
              payload={"goal": goal, "standard": standard})

    from app.graph.state import WorkflowStage
    initial: PipelineState = {
        "run_id": run_id,
        "goal": goal,
        "standard": standard or goal,
        "stage": WorkflowStage.APPLICATION_RECEIVED,
        "next": "",
        "completed": [],
        "messages": [],
        "corpus": corpus,
    }
    final_state = await SUPERVISOR.ainvoke(initial)

    log_event(
        run_id,
        source="manager",
        event_type="run_completed",
        payload={
            "completed": final_state.get("completed", []),
            "top_candidate": final_state.get("top_candidate"),
            "needs_review": final_state.get("needs_review", False),
        },
    )
    return {"run_id": run_id, "final_state": final_state}
