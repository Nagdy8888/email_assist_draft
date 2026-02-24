"""
Run the email assistant graph.

Use cases: load .env, build/compile the simple agent (Phase 2), invoke with
a user message and thread_id, print the last (assistant) message. Multi-turn
works by reusing the same thread_id.
"""

import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from langgraph.checkpoint.memory import MemorySaver

from email_assistant.simple_agent import build_simple_graph


def main() -> None:
    load_dotenv()
    graph = build_simple_graph(checkpointer=MemorySaver())
    thread_id = os.getenv("THREAD_ID", "default-thread")
    config = {"configurable": {"thread_id": thread_id}}

    # Phase 2: single user message → response
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
