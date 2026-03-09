"""
Entry: build and compile the top-level graph with two subagents (Email Assistant, Response).

Use cases: one agent (START → input_router → email_assistant subgraph or prepare_messages → response_agent subgraph → mark_as_read).
Phase 6: optional store for memory (triage/response/cal preferences); HITL for notify and for send_email/schedule_meeting.
"""

import os

from langgraph.config import get_config
from langgraph.graph import END, START, StateGraph

from email_assistant.memory import get_memory
from email_assistant.schemas import State, StateInput
from email_assistant.nodes.input_router import input_router
from email_assistant.nodes.triage import triage_router
from email_assistant.nodes.triage_interrupt import triage_interrupt_handler
from email_assistant.nodes.prepare_messages import prepare_messages
from email_assistant.nodes.mark_as_read import mark_as_read_node
from email_assistant.simple_agent import build_response_subgraph


def _make_triage_node(store=None):
    """When store is set, load triage_preferences and call triage_router with triage_instructions."""

    def triage_node(state: State) -> dict:
        triage_instructions = ""
        if store is not None:
            config = get_config()
            user_id = (config.get("configurable") or {}).get("user_id", os.getenv("USER_ID", "default-user"))
            triage_instructions = get_memory(store, user_id, "triage_preferences") or ""
        return triage_router(state, triage_instructions=triage_instructions)

    return triage_node


def _after_triage_route(state: State) -> str:
    """Inside Email Assistant subgraph: ignore/respond → END, notify → triage_interrupt_handler."""
    decision = (state.get("classification_decision") or "").strip().lower()
    if decision == "notify":
        return "triage_interrupt_handler"
    return "__end__"


def build_email_assistant_subgraph(store=None):
    """
    Build the Email Assistant subgraph: triage_router → ignore/respond → END, notify → triage_interrupt_handler → END.

    When store is set, triage node loads triage_preferences from memory.
    """
    builder = StateGraph(State)
    builder.add_node("triage_router", _make_triage_node(store))
    builder.add_node("triage_interrupt_handler", triage_interrupt_handler)
    builder.add_edge(START, "triage_router")
    builder.add_conditional_edges("triage_router", _after_triage_route, {
        "triage_interrupt_handler": "triage_interrupt_handler",
        "__end__": END,
    })
    builder.add_edge("triage_interrupt_handler", END)
    return builder.compile()


def _after_input_router_route(state: State) -> str:
    """Route from input_router: email path → email_assistant subgraph, question path → prepare_messages."""
    if state.get("email_input"):
        return "email_assistant"
    return "prepare_messages"


def _after_email_assistant_route(state: State) -> str:
    """After Email Assistant subgraph: respond → prepare_messages, else END."""
    if (state.get("classification_decision") or "").strip().lower() == "respond":
        return "prepare_messages"
    if (state.get("_notify_choice") or "").strip().lower() == "respond":
        return "prepare_messages"
    return "__end__"


def build_email_assistant_graph(checkpointer=None, store=None):
    """
    Build and compile the one agent with two subagents.

    Flow: START → input_router → (email_input ? email_assistant subgraph : prepare_messages)
    - email_assistant subgraph → (respond ? prepare_messages : END)
    - prepare_messages → response_agent subgraph → mark_as_read → END

    When store is set (Phase 6), triage and response agent use get_memory for preferences.
    """
    email_subgraph = build_email_assistant_subgraph(store=store)
    response_subgraph = build_response_subgraph(checkpointer=checkpointer, store=store)

    builder = StateGraph(State, input_schema=StateInput)
    builder.add_node("input_router", input_router)
    builder.add_node("email_assistant", email_subgraph)
    builder.add_node("prepare_messages", prepare_messages)
    builder.add_node("response_agent", response_subgraph)
    builder.add_node("mark_as_read", mark_as_read_node)

    builder.add_edge(START, "input_router")
    builder.add_conditional_edges("input_router", _after_input_router_route, {
        "email_assistant": "email_assistant",
        "prepare_messages": "prepare_messages",
    })
    builder.add_conditional_edges("email_assistant", _after_email_assistant_route, {
        "prepare_messages": "prepare_messages",
        "__end__": END,
    })
    builder.add_edge("prepare_messages", "response_agent")
    builder.add_edge("response_agent", "mark_as_read")
    builder.add_edge("mark_as_read", END)

    # When run under LangGraph API (Studio), do not pass a checkpointer; the API provides one.
    # For CLI (run_agent.py), pass an explicit checkpointer (e.g. MemorySaver()) for HITL/threads.
    if checkpointer is not None and store is not None:
        return builder.compile(checkpointer=checkpointer, store=store)
    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer)
    if store is not None:
        return builder.compile(store=store)
    return builder.compile()


# For LangGraph Studio: export graph without checkpointer so the API can load it.
email_assistant = build_email_assistant_graph()
