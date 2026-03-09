"""
Run the email assistant graph.

Use cases: load .env, build/compile the Phase 5 graph (input_router → triage or response_agent),
invoke with user_message (question mode) or email_input (email mode), print the last message.
When DATABASE_URL is set, the graph uses Postgres checkpointer; messages are persisted via
the response_agent subgraph. For notify path, the graph pauses at interrupt(); prompt the user
to choose respond or ignore, then resume with Command(resume="respond") or Command(resume="ignore").
"""

import os

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from email_assistant.email_assistant_hitl_memory_gmail import build_email_assistant_graph
from email_assistant.db.checkpointer import postgres_checkpointer


def main() -> None:
    load_dotenv()
    thread_id = os.getenv("THREAD_ID", "default-thread")
    user_id = os.getenv("USER_ID", "default-user")
    config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}

    database_url = os.getenv("DATABASE_URL")
    # When DATABASE_URL is set, use Postgres checkpointer and store (Phase 6 memory).
    if database_url:
        from email_assistant.db.store import postgres_store
        with postgres_checkpointer() as checkpointer:
            with postgres_store() as store:
                graph = build_email_assistant_graph(checkpointer=checkpointer, store=store)
                _run(graph, config)
    else:
        graph = build_email_assistant_graph(checkpointer=MemorySaver())
        _run(graph, config)


def _run(graph, config: dict) -> None:
    """Invoke graph with RUN_MESSAGE (question) or RUN_EMAIL_* (email mode). On notify interrupt, prompt and resume."""
    # Optional: email mode via env (for testing)
    email_from = os.getenv("RUN_EMAIL_FROM")
    email_subject = os.getenv("RUN_EMAIL_SUBJECT")
    email_body = os.getenv("RUN_EMAIL_BODY", "")
    if email_from and email_subject is not None:
        input_state = {
            "email_input": {
                "from": email_from,
                "to": os.getenv("RUN_EMAIL_TO", ""),
                "subject": email_subject,
                "body": email_body,
                "id": os.getenv("RUN_EMAIL_ID"),
            }
        }
    else:
        initial_message = os.getenv("RUN_MESSAGE", "Hello, how are you?")
        input_state = {"user_message": initial_message}

    result = graph.invoke(input_state, config=config)

    while result.get("__interrupt__"):
        interrupt_payload = result["__interrupt__"]
        msg = interrupt_payload if isinstance(interrupt_payload, str) else (interrupt_payload.get("message") or interrupt_payload)
        print("Graph paused:", msg)
        if isinstance(interrupt_payload, dict) and "tool_calls" in interrupt_payload:
            raw = input("Approve tool execution? (y/n) [y]: ").strip().lower()
            choice = raw != "n" and raw != "no"
        else:
            print("(Notify path: choose respond or ignore)")
            raw = input("Resume with (r)espond or (i)gnore? [r/i]: ").strip().lower()
            choice = "respond" if (raw.startswith("r") or raw == "respond") else "ignore"
        result = graph.invoke(Command(resume=choice), config=config)

    messages = result.get("messages", [])
    if messages:
        last = messages[-1]
        print(last.content if hasattr(last, "content") else last)
    else:
        print("(no messages in state)")
    if result.get("classification_decision"):
        print("Classification:", result["classification_decision"])
    if result.get("_notify_choice"):
        print("Notify choice:", result["_notify_choice"])


if __name__ == "__main__":
    main()
