"""
Run the email assistant graph.

Use cases: load .env, build/compile the simple agent (Phase 2/3), invoke with
a user message and thread_id, print the last (assistant) message. When
DATABASE_URL is set, the graph persists messages to email_assistant.messages
(via the persist_messages node); same when using LangSmith Studio.
"""

import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from langgraph.checkpoint.memory import MemorySaver

from email_assistant.simple_agent import build_simple_graph
from email_assistant.db.checkpointer import postgres_checkpointer


def main() -> None:
    load_dotenv()
    thread_id = os.getenv("THREAD_ID", "default-thread")
    user_id = os.getenv("USER_ID", "default-user")
    config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        with postgres_checkpointer() as checkpointer:
            graph = build_simple_graph(checkpointer=checkpointer)
            initial_message = os.getenv("RUN_MESSAGE", "Hello, how are you?")
            result = graph.invoke(
                {"messages": [HumanMessage(content=initial_message)]},
                config=config,
            )
    else:
        graph = build_simple_graph(checkpointer=MemorySaver())
        initial_message = os.getenv("RUN_MESSAGE", "Hello, how are you?")
        result = graph.invoke(
            {"messages": [HumanMessage(content=initial_message)]},
            config=config,
        )

    messages = result.get("messages", [])
    if messages:
        last = messages[-1]
        print(last.content if hasattr(last, "content") else last)
    else:
        print("(no messages in state)")


if __name__ == "__main__":
    main()
