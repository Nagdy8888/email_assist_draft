"""
Question and Done tools for the response agent.

Use cases: agent signals need for clarification (Question) or completion (Done);
used in tool-call loop so the agent can ask the user or signal end of turn.
"""

from langchain_core.tools import tool


@tool
def question_tool(message: str) -> str:
    """
    Ask the user a question or request clarification. Use when you need more information
    (e.g. missing recipient, unclear subject) before proceeding.
    """
    return f"[Question for user: {message}]"


@tool
def done_tool(summary: str = "") -> str:
    """
    Signal that you are done with this turn. Use after sending an email or completing
    the user's request. Optionally provide a short summary of what was done.
    """
    return f"Done.{' ' + summary if summary else ''}"
