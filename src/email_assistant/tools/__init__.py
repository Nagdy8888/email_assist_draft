"""
get_tools(include_gmail=...) and tool exports for the response agent.

Use cases: provide send_email_tool, fetch_emails_tool, check_calendar_tool,
schedule_meeting_tool, Question, Done to the LLM via bind_tools.
"""

from email_assistant.tools.common import done_tool, question_tool
from email_assistant.tools.gmail.send_email import send_email_tool


def get_tools(include_gmail: bool = True, include_calendar: bool = True):
    """
    Return list of tools for the response agent LLM (bind_tools).

    Use cases: pass to ChatOpenAI.bind_tools() in the chat/tool-call loop.
    include_gmail: send_email_tool and optionally fetch_emails_tool.
    include_calendar: check_calendar_tool, schedule_meeting_tool.
    """
    tools = [question_tool, done_tool]
    if include_gmail:
        tools.insert(0, send_email_tool)
        from email_assistant.tools.gmail.fetch_emails import fetch_emails_tool
        tools.append(fetch_emails_tool)
    if include_calendar:
        from email_assistant.tools.gmail.calendar import check_calendar_tool, schedule_meeting_tool
        tools.extend([check_calendar_tool, schedule_meeting_tool])
    return tools
