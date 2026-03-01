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
- **send_email_tool**: Send an email. For a NEW email to a specific recipient, call with:
  - email_address: recipient email
  - subject: subject line
  - body: body text
  Do not pass email_id when sending a new email.
  For REPLIES to an existing email (when the user says "reply to this email" or the context is a specific email), call with email_address, subject, body, AND email_id (the Gmail message id of the email you are replying to). Use this when the user says e.g. "send an email to X" or "reply to this email".
- **question_tool**: Ask the user for clarification when you need more info (e.g. recipient, subject).
- **done_tool**: Call when you have finished the request (e.g. after sending the email).

Today's date is {today}. Do not invent email addresses or content. When the user asks to send an email to a specific address, use send_email_tool with that address, subject, and body. When replying to an email in context, include the email_id argument."""

GMAIL_TOOLS_PROMPT = get_gmail_tools_prompt()
