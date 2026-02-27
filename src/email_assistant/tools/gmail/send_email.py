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
        # Phase 5: reply in thread (stub for now)
        raise NotImplementedError("Reply by email_id is implemented in Phase 5.")
    return send_new_email(to_email=email_address, subject=subject, body=body)
