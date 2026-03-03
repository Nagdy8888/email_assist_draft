"""
Gmail inbox watcher: poll Gmail for new emails and run the agent on each one automatically.

Use cases: run this script (e.g. in background or as a service) so the agent sees
any real email that arrives in Gmail. Fetches unread INBOX messages, invokes the graph
with each as email_input, then marks the message id as processed so it is not run again.
Requires Gmail OAuth (.secrets/credentials.json and .secrets/token.json) and OPENAI_API_KEY.

Example:
  uv run python scripts/watch_gmail.py
  GMAIL_POLL_INTERVAL=120 GMAIL_UNREAD_ONLY=1 uv run python scripts/watch_gmail.py
"""

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver

from email_assistant.email_assistant_hitl_memory_gmail import build_email_assistant_graph
from email_assistant.db.checkpointer import postgres_checkpointer
from email_assistant.tools.gmail.auth import get_gmail_service
from email_assistant.tools.gmail.fetch_emails import get_message_as_email_input, list_inbox_message_ids


def _processed_ids_path() -> Path:
    path = os.getenv("GMAIL_PROCESSED_IDS_FILE", "")
    if path:
        return Path(path)
    return Path(__file__).resolve().parents[1] / ".gmail_processed_ids.json"


def load_processed_ids() -> set[str]:
    p = _processed_ids_path()
    if not p.exists():
        return set()
    try:
        with open(p, "r") as f:
            data = json.load(f)
        return set(data.get("ids", []))
    except Exception:
        return set()


def save_processed_ids(ids: set[str], max_stored: int = 5000) -> None:
    """Persist processed ids so we do not re-process the same email."""
    p = _processed_ids_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    ids_list = list(ids)[-max_stored:]
    with open(p, "w") as f:
        json.dump({"ids": ids_list}, f, indent=0)


def main() -> None:
    load_dotenv()
    poll_interval = int(os.getenv("GMAIL_POLL_INTERVAL", "60"))
    unread_only = os.getenv("GMAIL_UNREAD_ONLY", "1").strip().lower() in ("1", "true", "yes")
    max_results = int(os.getenv("GMAIL_MAX_RESULTS", "20"))
    user_id = os.getenv("USER_ID", "default-user")

    try:
        service = get_gmail_service()
    except Exception as e:
        print("Gmail auth failed. Ensure .secrets/credentials.json and .secrets/token.json exist.", e)
        return

    processed = load_processed_ids()
    database_url = os.getenv("DATABASE_URL")
    # When DATABASE_URL is set, use Supabase Postgres so checkpoint data is stored in Supabase (run setup_db.py once).
    if database_url:
        with postgres_checkpointer() as checkpointer:
            graph = build_email_assistant_graph(checkpointer=checkpointer)
            print(f"Watching Gmail INBOX (unread_only={unread_only}, poll_interval={poll_interval}s). Press Ctrl+C to stop.")
            _run_loop(service, graph, processed, poll_interval, unread_only, max_results, user_id)
    else:
        graph = build_email_assistant_graph(checkpointer=MemorySaver())
        print(f"Watching Gmail INBOX (unread_only={unread_only}, poll_interval={poll_interval}s). Press Ctrl+C to stop.")
        _run_loop(service, graph, processed, poll_interval, unread_only, max_results, user_id)


def _run_loop(service, graph, processed: set[str], poll_interval: int, unread_only: bool, max_results: int, user_id: str) -> None:
    first_poll = True
    while True:
        try:
            ids = list_inbox_message_ids(service, max_results=max_results, unread_only=unread_only)
            if first_poll and not ids:
                print("No messages from Gmail INBOX. Try GMAIL_UNREAD_ONLY=0 to fetch recent (not only unread), or check OAuth scopes include gmail.readonly.")
            first_poll = False
            for message_id in ids:
                if message_id in processed:
                    continue
                try:
                    email_input = get_message_as_email_input(service, message_id)
                except Exception as e:
                    print(f"[{message_id}] Gmail get failed: {e}")
                    continue
                if not email_input:
                    print(f"[{message_id}] Could not fetch message (API error or missing body). Skipping.")
                    continue
                thread_id = f"gmail-{message_id}"
                config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}
                try:
                    result = graph.invoke({"email_input": email_input}, config=config)
                    processed.add(message_id)
                    save_processed_ids(processed)
                    decision = result.get("classification_decision", "")
                    from_addr = (email_input.get("from") or "")[:40]
                    subj = (email_input.get("subject") or "")[:50]
                    print(f"[{thread_id}] {decision} | From: {from_addr} | Subject: {subj}")
                    if result.get("__interrupt__"):
                        print("  -> Notify: graph paused; resume with Command(resume='respond') or Command(resume='ignore')")
                except Exception as e:
                    print(f"[{thread_id}] invoke failed: {e}")
        except Exception as e:
            print(f"Poll error (Gmail list or auth): {e}")
        time.sleep(poll_interval)


if __name__ == "__main__":
    main()
