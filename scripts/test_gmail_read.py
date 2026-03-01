"""
Test Gmail read access: list INBOX message ids and optionally fetch one.

Use cases: verify OAuth and gmail.readonly scope so the graph/watcher can read emails.
Run from repo root: uv run python scripts/test_gmail_read.py

If this fails, fix auth (e.g. re-run OAuth so token has gmail.readonly) before using the watcher.
"""

import os
import sys

from dotenv import load_dotenv

# Add project root so email_assistant is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from email_assistant.tools.gmail.auth import get_gmail_service
from email_assistant.tools.gmail.fetch_emails import get_message_as_email_input, list_inbox_message_ids


def main() -> None:
    load_dotenv()
    print("Testing Gmail read access...")
    try:
        service = get_gmail_service()
    except Exception as e:
        print("Gmail auth failed:", e)
        print("Ensure .secrets/credentials.json and .secrets/token.json exist and token has gmail.readonly scope.")
        return
    print("Auth OK.")
    try:
        ids = list_inbox_message_ids(service, max_results=5, unread_only=False)
    except Exception as e:
        print("Gmail list INBOX failed:", e)
        print("Check that your OAuth token includes gmail.readonly (re-run OAuth if needed).")
        return
    print(f"INBOX (recent 5): {len(ids)} message(s)", ids[:5] if ids else "none")
    if not ids:
        print("No messages in INBOX. Send yourself a test email or use another account.")
        return
    mid = ids[0]
    email_input = get_message_as_email_input(service, mid)
    if not email_input:
        print("Could not fetch message body (API error or permissions). Check gmail.readonly scope.")
        return
    print("First message:", email_input.get("subject"), "| From:", (email_input.get("from") or "")[:50])
    print("Gmail read test OK. You can run the watcher: uv run python scripts/watch_gmail.py")


if __name__ == "__main__":
    main()
