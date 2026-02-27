"""
get_tools(include_gmail=...) and tool exports for the response agent.

Use cases: provide send_email_tool, fetch_emails_tool, check_calendar_tool,
schedule_meeting_tool, Question, Done to the LLM via bind_tools.
"""

from email_assistant.tools.common import done_tool, question_tool
from email_assistant.tools.gmail.send_email import send_email_tool


def get_tools(include_gmail: bool = True):
    """
    Return list of tools for the response agent LLM (bind_tools).

    Use cases: pass to ChatOpenAI.bind_tools() in the chat/tool-call loop.
    Phase 4: send_email_tool, question_tool, done_tool. Optional fetch/calendar later.
    """
    tools = [question_tool, done_tool]
    if include_gmail:
        tools.insert(0, send_email_tool)
    return tools
