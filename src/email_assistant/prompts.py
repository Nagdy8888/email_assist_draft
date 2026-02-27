"""
Triage, agent, and memory-update prompts; default_* constants.

Use cases: centralize system prompts for triage router, response agent, and
memory-update LLM; keep prompt text out of node code.
"""

# Phase 2: system prompt for the simple Q&A agent (no tools, no triage).
SIMPLE_AGENT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's questions clearly and concisely."
)

# Phase 4: system prompt for the agent with tools (send email, question, done).
def get_agent_system_prompt_with_tools() -> str:
    """System prompt for response agent with send_email_tool and question/done."""
    from email_assistant.tools.gmail.prompt_templates import get_gmail_tools_prompt
    return (
        "You are a helpful assistant. You can send emails on the user's behalf and answer questions. "
        "When the user asks you to send an email to a specific address, use send_email_tool with "
        "email_address, subject, and body (do not use email_id for new emails). "
        "When you need clarification, use question_tool. When you have completed the request, use done_tool.\n\n"
        + get_gmail_tools_prompt()
    )
