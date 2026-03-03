"""
Simulate what happens when the graph receives a real email from the Gmail API.

Use cases: run the full flow (input_router → triage → notify/respond/ignore;
when notify, agent auto-decides respond or ignore) using a mock email with the
same shape the watcher would pass. No Gmail API or OAuth required. Set OPENAI_API_KEY.

Example:
  uv run python scripts/simulate_gmail_email.py
  SIMULATE_EMAIL=respond uv run python scripts/simulate_gmail_email.py
"""

import os
import sys

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver

from email_assistant.email_assistant_hitl_memory_gmail import build_email_assistant_graph
from email_assistant.db.checkpointer import postgres_checkpointer
from email_assistant.fixtures.mock_emails import get_mock_email


def main() -> None:
    load_dotenv()
    fixture_name = os.getenv("SIMULATE_EMAIL", "notify").strip().lower()
    if len(sys.argv) > 1:
        fixture_name = sys.argv[1].strip().lower()
    thread_id = os.getenv("THREAD_ID", "simulate-gmail-1")
    user_id = os.getenv("USER_ID", "default-user")
    config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}

    email_input = get_mock_email(fixture_name)
    print("=== Simulation: graph receiving an email (as if from Gmail API) ===")
    print(f"From: {email_input.get('from')}")
    print(f"To: {email_input.get('to')}")
    print(f"Subject: {email_input.get('subject')}")
    print(f"Body: {email_input.get('body', '')[:80]}...")
    print("(Payload shape is the same as watch_gmail.py would pass from Gmail API.)")
    print()

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        with postgres_checkpointer() as checkpointer:
            graph = build_email_assistant_graph(checkpointer=checkpointer)
            _simulate(graph, config, email_input)
    else:
        graph = build_email_assistant_graph(checkpointer=MemorySaver())
        _simulate(graph, config, email_input)


def _simulate(graph, config: dict, email_input: dict) -> None:
    print("Step 1: Invoking graph with email_input...")
    result = graph.invoke({"email_input": email_input}, config=config)

    classification = result.get("classification_decision") or "(none)"
    print(f"Step 2: Triage result: {classification}")

    if classification == "notify":
        notify_choice = result.get("_notify_choice") or "(none)"
        print(f"Step 3: Notify path - agent auto-decided: {notify_choice}.")
    elif classification == "respond":
        print("Step 3: Respond path - prepare_messages, response_agent, mark_as_read ran.")
    elif classification == "ignore":
        print("Step 3: Ignore path - graph ended (no response, no mark_as_read).")

    messages = result.get("messages", [])
    if messages:
        last = messages[-1]
        content = getattr(last, "content", str(last))
        print("Final state: last message:", (content[:200] + "..." if len(str(content)) > 200 else content))
    else:
        print("Final state: no messages in state.")
    print("=== Simulation done ===")


if __name__ == "__main__":
    main()
