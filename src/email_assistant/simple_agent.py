"""
Simple agent: user message → single LLM response. Phase 2 minimal agent.

Use cases: validate LangGraph + OpenAI + optional LangSmith; one node that calls
ChatOpenAI with state["messages"], multi-turn via InMemorySaver and thread_id.
No DB, no store, no email. Extended in later phases to full graph.
Persists messages to Supabase/Postgres when DATABASE_URL is set (CLI and LangSmith Studio).
"""

import os

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import get_config
from langgraph.graph import END, START, StateGraph

from email_assistant.prompts import SIMPLE_AGENT_SYSTEM_PROMPT
from email_assistant.schemas import MessagesState


def _chat_node(state: MessagesState) -> dict:
    """
    Single node: invoke ChatOpenAI on current messages and return new assistant message.

    Use cases: called by the simple graph each turn; append-only messages via add_messages.
    """
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    # Build messages: system + conversation history
    from langchain_core.messages import SystemMessage

    messages = [SystemMessage(content=SIMPLE_AGENT_SYSTEM_PROMPT)] + list(
        state["messages"]
    )
    response = llm.invoke(messages)
    return {"messages": [response]}


def _persist_messages_node(state: MessagesState) -> dict:
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


def build_simple_graph(checkpointer=None):
    """
    Build and compile the Phase 2 simple graph: START → chat → persist_messages → END.

    Use cases: run script imports this, compiles with MemorySaver for multi-turn;
    LangGraph Studio uses compile() with no checkpointer (platform handles persistence).
    When DATABASE_URL is set, persist node writes messages to Supabase/Postgres.
    """
    builder = StateGraph(MessagesState)
    builder.add_node("chat", _chat_node)
    builder.add_node("persist_messages", _persist_messages_node)
    builder.add_edge(START, "chat")
    builder.add_edge("chat", "persist_messages")
    builder.add_edge("persist_messages", END)
    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()


# For LangGraph Studio: langgraph dev loads this via langgraph.json. No checkpointer—
# the platform provides persistence when run via Studio / LangGraph API.
graph = build_simple_graph()
