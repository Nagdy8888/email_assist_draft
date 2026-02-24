"""
Simple agent: user message → single LLM response. Phase 2 minimal agent.

Use cases: validate LangGraph + OpenAI + optional LangSmith; one node that calls
ChatOpenAI with state["messages"], multi-turn via InMemorySaver and thread_id.
No DB, no store, no email. Extended in later phases to full graph.
"""

import os

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
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


def build_simple_graph(checkpointer=None):
    """
    Build and compile the Phase 2 simple graph: START → chat_node → END.

    Use cases: run script imports this, compiles with MemorySaver for multi-turn;
    LangGraph Studio uses compile() with no checkpointer (platform handles persistence).
    """
    builder = StateGraph(MessagesState)
    builder.add_node("chat", _chat_node)
    builder.add_edge(START, "chat")
    builder.add_edge("chat", END)
    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()


# For LangGraph Studio: langgraph dev loads this via langgraph.json. No checkpointer—
# the platform provides persistence when run via Studio / LangGraph API.
graph = build_simple_graph()
