"""
parse_gmail, format_gmail_markdown, format_for_display and other helpers.

Use cases: parse Gmail-style payloads, format email content for LLM or UI display,
and shared formatting used by nodes and tools.
"""

from typing import Any, Optional


def _header(headers: list[dict], name: str) -> str:
    """Get first header value by name (case-insensitive)."""
    name_lower = name.lower()
    for h in headers:
        if (h.get("name") or "").lower() == name_lower:
            return (h.get("value") or "").strip()
    return ""


def parse_gmail(payload: dict) -> dict:
    """
    Parse a Gmail API message payload into a flat email_input-style dict.

    Use cases: convert Gmail API response (e.g. from fetch_emails or webhook) into
    the shape expected by input_router and triage (from, to, subject, body, id).

    Example:
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        email_input = parse_gmail(msg.get("payload") or {})
    """
    if not payload or not isinstance(payload, dict):
        return {"from": "", "to": "", "subject": "", "body": "", "id": None}
    headers = payload.get("headers") or []
    body_struct = payload.get("body") or {}
    body_data = body_struct.get("data")
    body = ""
    if body_data:
        import base64
        try:
            body = base64.urlsafe_b64decode(body_data.encode("ASCII")).decode("utf-8", errors="replace")
        except Exception:
            pass
    if not body and payload.get("parts"):
        for part in payload.get("parts") or []:
            if (part.get("mimeType") or "").lower() in ("text/plain", "text/html"):
                part_body = part.get("body") or {}
                part_data = part_body.get("data")
                if part_data:
                    import base64
                    try:
                        body = base64.urlsafe_b64decode(part_data.encode("ASCII")).decode("utf-8", errors="replace")
                        break
                    except Exception:
                        pass
    return {
        "from": _header(headers, "From"),
        "to": _header(headers, "To"),
        "subject": _header(headers, "Subject"),
        "body": body,
        "id": None,
    }


def format_gmail_markdown(email: dict, max_body_chars: int = 8000) -> str:
    """
    Format an email_input-style dict as markdown for LLM consumption.

    Use cases: triage user prompt, response agent context, or any place the model
    needs to read "From / To / Subject / Body" in a consistent format.

    Example:
        md = format_gmail_markdown({"from": "a@b.com", "to": "c@d.com", "subject": "Hi", "body": "Hello"})
    """
    from_addr = (email.get("from") or "").strip()
    to_addr = (email.get("to") or "").strip()
    subject = (email.get("subject") or "").strip()
    body = (email.get("body") or "").strip()
    if max_body_chars and len(body) > max_body_chars:
        body = body[:max_body_chars] + "\n..."
    return f"""- **From:** {from_addr}
- **To:** {to_addr}
- **Subject:** {subject}

## Body

{body}"""


def format_for_display(email: dict, body_snippet_len: int = 200) -> str:
    """
    Format an email for short UI display (e.g. inbox list or notification).

    Use cases: scripts or UI that show "From / Subject / snippet" without full body.

    Example:
        line = format_for_display({"from": "a@b.com", "subject": "Hi", "body": "Long body..."})
    """
    from_addr = (email.get("from") or "").strip()
    subject = (email.get("subject") or "").strip()
    body = (email.get("body") or "").strip().replace("\n", " ")
    if body_snippet_len and len(body) > body_snippet_len:
        body = body[:body_snippet_len] + "..."
    return f"From: {from_addr} | Subject: {subject} | {body}"
