"""
Fetch emails from Gmail for automatic ingestion into the agent.

Use cases: list recent/unread inbox messages; convert a Gmail message to email_input
so the graph can run triage and response. Used by the Gmail watcher script to feed
real emails into the agent automatically.
"""

import base64
from typing import Optional

from langchain_core.tools import tool

from email_assistant.tools.gmail.auth import get_gmail_service


def _header(msg: dict, name: str) -> str:
    """Get a header value from Gmail message payload."""
    payload = msg.get("payload") or {}
    for h in payload.get("headers") or []:
        if (h.get("name") or "").lower() == name.lower():
            return (h.get("value") or "").strip()
    return ""


def _decode_body(payload: dict) -> str:
    """Extract plain text body from Gmail payload (single or multipart)."""
    if not payload:
        return ""
    # Single-part: payload.body.data (base64url)
    body = payload.get("body") or {}
    data = body.get("data")
    if data:
        try:
            return base64.urlsafe_b64decode(data.encode("ASCII")).decode("utf-8", errors="replace")
        except Exception:
            return ""
    # Multipart: find first text/plain or text/html part
    for part in payload.get("parts") or []:
        mimetype = (part.get("mimeType") or "").lower()
        if "text/plain" in mimetype or "text/html" in mimetype:
            part_body = part.get("body") or {}
            part_data = part_body.get("data")
            if part_data:
                try:
                    return base64.urlsafe_b64decode(part_data.encode("ASCII")).decode("utf-8", errors="replace")
                except Exception:
                    pass
    return ""


def get_message_as_email_input(service, message_id: str) -> Optional[dict]:
    """
    Fetch a Gmail message by id and return it in email_input shape for the graph.

    Returns dict with from, to, subject, body, id (and _source will be set by input_router).
    Returns None if the message cannot be fetched.
    """
    try:
        msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    except Exception:
        return None
    payload = msg.get("payload") or {}
    body = _decode_body(payload)
    snippet = (msg.get("snippet") or "").strip()
    if not body and snippet:
        body = snippet
    return {
        "from": _header(msg, "From"),
        "to": _header(msg, "To"),
        "subject": _header(msg, "Subject"),
        "body": body[:8000] if body else snippet[:8000],
        "id": msg.get("id"),
    }


def list_inbox_message_ids(
    service,
    max_results: int = 20,
    unread_only: bool = False,
    query: Optional[str] = None,
) -> list[str]:
    """
    List message ids from the user's INBOX.

    Use cases: watcher uses this to find new emails to process.
    """
    label_ids = ["INBOX"]
    q = "is:unread" if unread_only else None
    if query:
        q = f"{q} {query}".strip() if q else query
    try:
        result = service.users().messages().list(
            userId="me",
            labelIds=label_ids,
            maxResults=max_results,
            q=q,
        ).execute()
    except Exception as e:
        raise RuntimeError(f"Gmail API list failed: {e}") from e
    return [m["id"] for m in result.get("messages", [])]


def fetch_recent_inbox(
    service=None,
    max_results: int = 20,
    unread_only: bool = False,
) -> list[dict]:
    """
    Fetch recent INBOX messages and return them as email_input dicts.

    Use cases: Gmail watcher calls this to get new emails to pass into the graph.
    """
    if service is None:
        service = get_gmail_service()
    ids = list_inbox_message_ids(service, max_results=max_results, unread_only=unread_only)
    out = []
    for mid in ids:
        email_input = get_message_as_email_input(service, mid)
        if email_input:
            out.append(email_input)
    return out


def _fetch_emails_impl(max_results: int = 10, unread_only: bool = False) -> str:
    """Fetch recent inbox and return summary text."""
    from email_assistant.utils import format_for_display
    try:
        emails = fetch_recent_inbox(max_results=max_results, unread_only=unread_only)
    except Exception as e:
        return f"Failed to fetch emails: {e}"
    if not emails:
        return "No emails found."
    return "\n".join(format_for_display(e, body_snippet_len=80) for e in emails)


@tool
def fetch_emails_tool(max_results: int = 10, unread_only: bool = False) -> str:
    """
    List recent inbox emails. Use when the user asks what emails they have or to check their inbox.
    """
    return _fetch_emails_impl(max_results=max_results, unread_only=unread_only)
