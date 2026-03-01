"""
mark_as_read: Gmail API call to mark a message as read by id.

Use cases: called from mark_as_read node after response_agent finishes for email mode.
Requires gmail.modify scope.
"""

from email_assistant.tools.gmail.auth import get_gmail_service


def mark_as_read(email_id: str) -> str:
    """
    Mark the Gmail message with the given id as read (remove UNREAD label).

    Use cases: after the agent has replied to an email, mark the original as read.
    """
    if not email_id or not email_id.strip():
        return "No email_id provided; nothing to mark as read."
    service = get_gmail_service()
    service.users().messages().modify(
        userId="me",
        id=email_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()
    return f"Message {email_id} marked as read."
