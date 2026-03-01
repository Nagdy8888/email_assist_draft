"""
mark_as_read_node: mark email as read when email_id present; no-op when no email_id.

Use cases: after response_agent finishes, mark the source email read in Gmail
for email mode; question-only mode has no email_id so this node no-ops.
"""

from email_assistant.schemas import State
from email_assistant.tools.gmail.mark_as_read import mark_as_read as gmail_mark_as_read


def mark_as_read_node(state: State) -> dict:
    """
    Call Gmail mark_as_read(email_id) when state has email_id; otherwise no-op.

    Use cases: run after response_agent on the respond path so the triaged email is marked read.
    """
    email_id = state.get("email_id")
    if not email_id or not str(email_id).strip():
        return {}
    try:
        gmail_mark_as_read(str(email_id))
    except Exception:
        pass  # Don't fail the graph if Gmail API fails
    return {}
