"""
input_router: route by email_input vs user_message/question (email path vs question path).

Use cases: entry node that normalizes input into state; conditional edge from this node
sends to triage_router when email_input is present, else to response_agent (question mode).
"""

from langchain_core.messages import HumanMessage

from email_assistant.schemas import State


def _normalize_email_input(email_input: dict | None) -> dict | None:
    """Ensure email_input has from, to, subject, body; support Gmail-style payload or flat dict.
    Sets _source to 'gmail' when the payload has a Gmail message id or Gmail API structure so the agent knows it is an incoming message from the user's Gmail inbox."""
    if not email_input or not isinstance(email_input, dict):
        return None
    # Unwrap double-nested email_input (e.g. Studio run input sometimes as {"email_input": {"email_input": {...}}}).
    if set(email_input.keys()) <= {"email_input"} and isinstance(email_input.get("email_input"), dict):
        email_input = email_input["email_input"]
    has_gmail_id = bool(email_input.get("id"))
    payload = email_input.get("payload") or {}
    headers = payload.get("headers") or []
    is_gmail_api = bool(payload or headers)
    from_gmail = has_gmail_id or is_gmail_api

    # Flat dict (Studio/mock)
    if "from" in email_input or "subject" in email_input:
        out = {
            "from": email_input.get("from", ""),
            "to": email_input.get("to", ""),
            "subject": email_input.get("subject", ""),
            "body": email_input.get("body", email_input.get("snippet", "")),
            "id": email_input.get("id"),
        }
        if from_gmail:
            out["_source"] = "gmail"
        return out
    # Gmail API payload: payload.headers + id, threadId
    def h(name: str) -> str:
        for x in headers:
            if (x.get("name") or "").lower() == name.lower():
                return (x.get("value") or "").strip()
        return ""
    out = {
        "from": h("from"),
        "to": h("to"),
        "subject": h("subject"),
        "body": email_input.get("snippet") or payload.get("body", {}).get("data") or "",
        "id": email_input.get("id"),
    }
    if from_gmail:
        out["_source"] = "gmail"
    return out


def input_router(state: State) -> dict:
    """
    Normalize input: if user_message or question provided, set messages to a single HumanMessage.
    Return state update; do not change email_input (used by conditional edge for routing).

    Use cases: first node after START; ensures messages exist for question path and
    email_input is normalized for triage path.
    """
    updates: dict = {}
    messages = list(state.get("messages") or [])
    user_message = state.get("user_message") or state.get("question")
    if user_message and isinstance(user_message, str):
        messages = [HumanMessage(content=user_message)]
        updates["messages"] = messages
    email_input = state.get("email_input")
    if email_input is not None:
        normalized = _normalize_email_input(email_input)
        if normalized:
            updates["email_input"] = normalized
            if normalized.get("id"):
                updates["email_id"] = str(normalized["id"])
    return updates
