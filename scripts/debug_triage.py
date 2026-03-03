"""
Debug triage: find why an email is classified as ignore instead of respond.

Use cases: run locally to verify _is_explicit_request() and triage_router() with
the same payload you send to LangGraph Studio.

  uv run python scripts/debug_triage.py
  uv run python scripts/debug_triage.py payload.json   # debug exact Studio run input

Checks:
1. email_input shape (keys, subject, body) — Studio might send different keys.
2. After input_router: normalized email_input (in case Studio sends different shape).
3. _is_explicit_request(subject, body) — does the override fire?
4. triage_router(state) — final classification_decision.
"""

import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from email_assistant.fixtures.mock_emails import MOCK_EMAIL_RESPOND
from email_assistant.nodes.input_router import input_router
from email_assistant.nodes.triage import _is_explicit_request, triage_router


def get_payload() -> dict:
    """Run input: either from file or default MOCK_EMAIL_RESPOND."""
    if len(sys.argv) > 1:
        path = sys.argv[1]
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        # Allow file to be {"email_input": {...}} or just {...} as email_input.
        if "email_input" in data:
            return data
        return {"email_input": data}
    return {"email_input": MOCK_EMAIL_RESPOND}


def main() -> None:
    payload = get_payload()
    email_input_raw = payload.get("email_input") or {}

    print("=== Debug Triage ===\n")
    print("0. Raw run input (email_input keys):", list(email_input_raw.keys()) if isinstance(email_input_raw, dict) else type(email_input_raw))
    if isinstance(email_input_raw, dict):
        print("   subject:", repr(email_input_raw.get("subject", "<missing>")))
        body_raw = email_input_raw.get("body", email_input_raw.get("snippet", ""))
        print("   body (first 150 chars):", repr(str(body_raw)[:150]))
    print()

    # Simulate graph: input_router then triage_router
    state_in = {"messages": [], "email_input": email_input_raw}
    updates = input_router(state_in)
    state_after_router = {**state_in, **updates}
    email_input = state_after_router.get("email_input")

    if not email_input:
        print("1. After input_router: email_input is MISSING or empty.")
        print("   >>> If you use the chat box in Studio, that sends user_message, not email_input.")
        print("   >>> Use the run input (e.g. 'Edit run input') and set JSON to: {\"email_input\": {\"from\": \"...\", \"to\": \"...\", \"subject\": \"...\", \"body\": \"...\"}}")
        return

    print("1. After input_router (normalized) — keys:", list(email_input.keys()))
    subject = email_input.get("subject", "")
    body = str(email_input.get("body", ""))[:8000]
    print("   subject:", repr(subject))
    print("   body (first 200 chars):", repr(body[:200]))
    print()

    print("2. _is_explicit_request(subject, body)")
    combined = f"{subject}\n{body}".lower()
    patterns = (
        "send me the", "send me a", "could you send", "can you send",
        "please send", "please reply", "reply with", "by friday", "by monday",
        "by end of", "q4 report", "the report",
    )
    matched = [p for p in patterns if p in combined]
    if matched:
        for p in matched:
            print(f"   MATCH: {p!r}")
        print(f"   Result: True -> override WILL fire")
    else:
        print("   No pattern matched. Result: False -> LLM will be called.")
    is_request = _is_explicit_request(str(subject), body)
    print()

    print("3. triage_router(state)")
    out = triage_router(state_after_router)
    decision = out.get("classification_decision", "<missing>")
    print(f"   classification_decision: {decision!r}")
    if decision != "respond":
        print("   >>> UNEXPECTED for 'send me the report' style email.")
        print("   >>> If Studio still shows 'ignore', ensure (1) run input uses key 'email_input', (2) langgraph dev was restarted after code changes.")
    else:
        print("   >>> OK: got respond.")
    print()

    print("4. Studio run input tip")
    print("   Run input must be JSON with key 'email_input'. Example:")
    ex = {"email_input": {"from": "x@y.com", "to": "me@example.com", "subject": "Send report", "body": "Can you send me the report by Friday?"}}
    print("   ", json.dumps(ex))
    if not os.getenv("OPENAI_API_KEY"):
        print("\n   Note: OPENAI_API_KEY not set; LLM would fail if override did not fire.")


if __name__ == "__main__":
    main()
