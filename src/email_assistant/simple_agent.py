"""
Response subgraph: chat → tool_approval_gate (if tool_calls) → tools or chat, else persist_messages. Used as subagent in the main agent.

Use cases: user can ask to send an email; agent uses send_email_tool and tool-call loop.
Phase 6: HITL approval before send_email/schedule_meeting; memory (response/cal preferences) when store is passed.
"""

import os

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.config import get_config
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from email_assistant.prompts import get_agent_system_prompt_with_tools, get_agent_system_prompt_hitl_memory
from email_assistant.schemas import State
from email_assistant.tools import get_tools


def _make_chat_node(store=None):
    """Build chat node; when store is set, use get_memory for response/cal preferences and get_agent_system_prompt_hitl_memory."""

    def _chat_node(state: State) -> dict:
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        tools = get_tools(include_gmail=True, include_calendar=True)
        llm_with_tools = llm.bind_tools(tools)
        if store is not None:
            config = get_config()
            user_id = (config.get("configurable") or {}).get("user_id", os.getenv("USER_ID", "default-user"))
            from email_assistant.memory import get_memory
            response_prefs = get_memory(store, user_id, "response_preferences") or ""
            cal_prefs = get_memory(store, user_id, "cal_preferences") or ""
            system_text = get_agent_system_prompt_hitl_memory(response_preferences=response_prefs, cal_preferences=cal_prefs)
        else:
            system_text = get_agent_system_prompt_with_tools()
        system = SystemMessage(content=system_text)
        messages = [system] + list(state.get("messages") or [])
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    return _chat_node


def _should_continue(state: State) -> str:
    """Route to tool_approval_gate if last message has tool_calls, else to persist."""
    messages = state.get("messages", [])
    if not messages:
        return "persist_messages"
    last = messages[-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tool_approval_gate"
    return "persist_messages"


def _after_approval(state: State) -> str:
    """After tool_approval_gate: if approved go to tools, else back to chat."""
    if state.get("_tool_approval") is True:
        return "tools"
    return "chat"


def _persist_messages_node(state: State) -> dict:
    """
    When DATABASE_URL is set, persist state["messages"] to email_assistant.messages.

    Use cases: run after chat so messages are stored when using CLI or LangSmith Studio.
    Reads thread_id and user_id from LangGraph config (get_config()).
    """
    conn_string = os.getenv("DATABASE_URL")
    if not conn_string or not state.get("messages"):
        return {}
    try:
        config = get_config()
        configurable = config.get("configurable") or {}
        thread_id = configurable.get("thread_id", "default-thread")
        user_id = configurable.get("user_id", os.getenv("USER_ID", "default-user"))
    except Exception:
        thread_id = "default-thread"
        user_id = os.getenv("USER_ID", "default-user")
    try:
        from email_assistant.db.persist_messages import persist_messages
        persist_messages(conn_string, thread_id, user_id, list(state["messages"]))
    except Exception:
        pass  # Don't fail the graph if DB write fails
    return {}


def build_response_subgraph(checkpointer=None, store=None):
    """
    Build and compile the Response subgraph: START → chat → [tool_approval_gate →] tools or persist_messages → END.

    When tool_calls present: chat → tool_approval_gate (HITL) → tools or chat. Phase 6: store enables memory in chat node.
    """
    from email_assistant.nodes.tool_approval import tool_approval_gate
    tools = get_tools(include_gmail=True, include_calendar=True)
    tool_node = ToolNode(tools)
    builder = StateGraph(State)
    builder.add_node("chat", _make_chat_node(store))
    builder.add_node("tool_approval_gate", tool_approval_gate)
    builder.add_node("tools", tool_node)
    builder.add_node("persist_messages", _persist_messages_node)
    builder.add_edge(START, "chat")
    builder.add_conditional_edges("chat", _should_continue, {"tool_approval_gate": "tool_approval_gate", "persist_messages": "persist_messages"})
    builder.add_conditional_edges("tool_approval_gate", _after_approval, {"tools": "tools", "chat": "chat"})
    builder.add_edge("tools", "chat")
    builder.add_edge("persist_messages", END)
    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()


# Backward compatibility for code that imports build_simple_graph.
build_simple_graph = build_response_subgraph
