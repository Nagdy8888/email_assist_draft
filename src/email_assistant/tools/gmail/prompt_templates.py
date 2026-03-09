"""
GMAIL_TOOLS_PROMPT and other Gmail-related prompt snippets for the response agent.

Use cases: system prompt text describing how to use send_email (reply vs new email),
fetch_emails, and calendar tools.
"""

from datetime import datetime

def get_gmail_tools_prompt() -> str:
    """Return the tools section for the agent system prompt (includes today's date)."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return f"""## Tools
- **send_email_tool**: Send an email. For a NEW email to a specific recipient, call with email_address, subject, body (no email_id). For REPLIES to an existing email, also pass email_id (Gmail message id).
- **fetch_emails_tool**: List recent inbox emails. Use when the user asks what emails they have or to check inbox.
- **check_calendar_tool**: List calendar events between start_date and end_date (YYYY-MM-DD). Use for "What's on my calendar?" or "Do I have meetings this week?"
- **schedule_meeting_tool**: Create a calendar event (summary, start_time, end_time in ISO format; optional description, location, attendees as comma-separated emails).
- **question_tool**: Ask the user for clarification when you need more info.
- **done_tool**: Call when you have finished the request.

Today's date is {today}. Do not invent email addresses, events, or content. When the user asks to send an email to a specific address, use send_email_tool. When replying to an email in context, include email_id. For calendar questions use check_calendar_tool; to create a meeting use schedule_meeting_tool."""

GMAIL_TOOLS_PROMPT = get_gmail_tools_prompt()
