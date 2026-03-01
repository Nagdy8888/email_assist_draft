"""
send_email_tool: send new email to a given address (Phase 4); reply by email_id (Phase 5).

Use cases: Gmail API to send new message or reply in thread; used by response agent
when user asks to "email X with subject Y" or when replying to triaged email.
"""

import base64
from email.mime.text import MIMEText
from typing import Optional

from langchain_core.tools import tool

from email_assistant.tools.gmail.auth import get_gmail_service


def _get_header(headers: list[dict], name: str) -> str:
    """Get first header value by name (case-insensitive)."""
    name_lower = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name_lower:
            return (h.get("value") or "").strip()
    return ""


def send_new_email(to_email: str, subject: str, body: str) -> str:
    """
    Send a new email via Gmail API (no reply thread).

    Use cases: called by send_email_tool when email_id is not provided.
    """
    service = get_gmail_service()
    message = MIMEText(body)
    message["to"] = to_email
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return f"Email sent to {to_email} (message id: {sent.get('id', '')})."


def send_reply_email(email_id: str, to_email: str, subject: str, body: str) -> str:
    """
    Send a reply in the same Gmail thread. Fetches original message for threadId and Message-ID.

    Use cases: called by send_email_tool when email_id is provided; keeps thread continuity.
    """
    service = get_gmail_service()
    orig = service.users().messages().get(userId="me", id=email_id, format="full").execute()
    payload = orig.get("payload") or {}
    headers = payload.get("headers") or []
    thread_id = orig.get("threadId", "")
    message_id_header = _get_header(headers, "Message-ID")
    orig_subject = _get_header(headers, "Subject")
    reply_subject = f"Re: {orig_subject}" if orig_subject and not subject.strip().lower().startswith("re:") else (subject or f"Re: {orig_subject}")

    message = MIMEText(body)
    message["to"] = to_email
    message["subject"] = reply_subject
    if message_id_header:
        message["In-Reply-To"] = message_id_header
        message["References"] = message_id_header

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body_send = {"raw": raw}
    if thread_id:
        body_send["threadId"] = thread_id
    sent = service.users().messages().send(userId="me", body=body_send).execute()
    return f"Reply sent in thread (message id: {sent.get('id', '')})."


@tool
def send_email_tool(
    email_address: str,
    subject: str,
    body: str,
    email_id: Optional[str] = None,
) -> str:
    """
    Send an email. Use for NEW emails: provide email_address (recipient), subject, and body.
    For replying to an existing email, provide email_id as well (Phase 5).
    """
    if email_id:
        return send_reply_email(
            email_id=email_id,
            to_email=email_address,
            subject=subject,
            body=body,
        )
    return send_new_email(to_email=email_address, subject=subject, body=body)
