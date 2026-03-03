"""
Run the graph with a mock email (no Gmail API).

Use cases: test triage and full flow without Gmail API. Uses mock email_input from
fixtures. When classification is notify, the graph pauses (interrupt) and prompts
you to choose respond or ignore; resume with Command(resume="respond") or
Command(resume="ignore"). When DATABASE_URL is set, checkpointer is Postgres (Supabase).

Example:
  uv run python scripts/run_mock_email.py
  MOCK_EMAIL=respond uv run python scripts/run_mock_email.py
"""

import os
import sys

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from email_assistant.email_assistant_hitl_memory_gmail import build_email_assistant_graph
from email_assistant.db.checkpointer import postgres_checkpointer
from email_assistant.fixtures.mock_emails import get_mock_email


def main() -> None:
    load_dotenv()
    # Fixture: notify (default, hits interrupt), respond, or ignore
    fixture_name = os.getenv("MOCK_EMAIL", "notify").strip().lower()
    if len(sys.argv) > 1:
        fixture_name = sys.argv[1].strip().lower()
    thread_id = os.getenv("THREAD_ID", "mock-hitl-1")
    user_id = os.getenv("USER_ID", "default-user")
    config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        with postgres_checkpointer() as checkpointer:
            graph = build_email_assistant_graph(checkpointer=checkpointer)
            _run(graph, config, fixture_name)
    else:
        graph = build_email_assistant_graph(checkpointer=MemorySaver())
        _run(graph, config, fixture_name)


def _run(graph, config: dict, fixture_name: str) -> None:
    email_input = get_mock_email(fixture_name)
    print(f"Using mock email: {fixture_name} | subject: {email_input.get('subject', '')[:50]}")
    result = graph.invoke({"email_input": email_input}, config=config)

    while result.get("__interrupt__"):
        print("Graph paused (notify path). The email was classified as notify (FYI).")
        print("Interrupt:", result["__interrupt__"])
        raw = input("Resume with (r)espond or (i)gnore? [r/i]: ").strip().lower()
        if raw.startswith("r") or raw == "respond":
            choice = "respond"
        else:
            choice = "ignore"
        result = graph.invoke(Command(resume=choice), config=config)

    _print_result(result)


def _print_result(result: dict) -> None:
    if result.get("classification_decision"):
        print("Classification:", result["classification_decision"])
    if result.get("_notify_choice"):
        print("Notify choice:", result["_notify_choice"])
    messages = result.get("messages", [])
    if messages:
        last = messages[-1]
        print("Last message:", last.content if hasattr(last, "content") else last)
    else:
        print("(no messages in state)")


if __name__ == "__main__":
    main()
