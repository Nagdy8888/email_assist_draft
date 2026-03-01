"""
Response subgraph: chat → tools → persist_messages. Used as subagent in the main agent.

Use cases: user can ask to send an email; agent uses send_email_tool and tool-call loop.
Persists messages to Supabase/Postgres when DATABASE_URL is set. Exposed as build_response_subgraph().
"""

import os

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.config import get_config
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from email_assistant.prompts import get_agent_system_prompt_with_tools
from email_assistant.schemas import State
from email_assistant.tools import get_tools


def _chat_node(state: State) -> dict:
    """
    Call LLM with tools; return the assistant message (may contain tool_calls).

    Use cases: first step in tool loop; when no tool_calls, next node is persist then END.
    """
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    tools = get_tools(include_gmail=True)
    llm_with_tools = llm.bind_tools(tools)
    system = SystemMessage(content=get_agent_system_prompt_with_tools())
    messages = [system] + list(state["messages"])
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def _should_continue(state: State) -> str:
    """Route to tools if last message has tool_calls, else to persist."""
    messages = state.get("messages", [])
    if not messages:
        return "persist_messages"
    last = messages[-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    return "persist_messages"


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


def build_response_subgraph(checkpointer=None):
    """
    Build and compile the Response subgraph: START → chat → (tools → chat)* → persist_messages → END.

    Use cases: added as a node to the main agent; when DATABASE_URL is set, messages are persisted.
    """
    tools = get_tools(include_gmail=True)
    tool_node = ToolNode(tools)
    builder = StateGraph(State)
    builder.add_node("chat", _chat_node)
    builder.add_node("tools", tool_node)
    builder.add_node("persist_messages", _persist_messages_node)
    builder.add_edge(START, "chat")
    builder.add_conditional_edges("chat", _should_continue, {"tools": "tools", "persist_messages": "persist_messages"})
    builder.add_edge("tools", "chat")
    builder.add_edge("persist_messages", END)
    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()


# Backward compatibility for code that imports build_simple_graph.
build_simple_graph = build_response_subgraph
