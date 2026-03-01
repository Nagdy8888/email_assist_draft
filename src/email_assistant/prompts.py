"""
Triage, agent, and memory-update prompts; default_* constants.

Use cases: centralize system prompts for triage router, response agent, and
memory-update LLM; keep prompt text out of node code.
"""

# Phase 2: system prompt for the simple Q&A agent (no tools, no triage).
SIMPLE_AGENT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's questions clearly and concisely."
)

# Phase 5: triage prompts and defaults.
DEFAULT_TRIAGE_INSTRUCTIONS = """## Triage categories (use exactly one)
- **ignore**: No action needed; low value or noise. Examples: marketing newsletters, automated receipts, out-of-office replies, broad announcements that do not require your response. Do NOT use ignore when the user is asking the assistant to send an email or take an action.
- **notify**: User should see it but no reply needed. Examples: deploy completions, HR deadline reminders, status updates, FYI items.
- **respond**: Needs a direct reply or action from the user or from the assistant. Examples: direct questions to you, meeting requests, client or manager asks, anything that explicitly asks for a response or action. **Always use respond when the content is the user asking to send an email, send a message, or perform an action** (e.g. "send an email to X", "send this to Gmail", "reply to this") so the assistant can use its tools.

When in doubt between ignore and notify, prefer **notify**. When in doubt between notify and respond, prefer **respond** when a direct reply or action is requested. If the body looks like a user instruction or request (e.g. to send an email), classify as **respond**."""


def get_triage_system_prompt(background: str = "", triage_instructions: str = "") -> str:
    """System prompt for triage router LLM. Injects background and triage_instructions (from memory or default)."""
    from datetime import datetime
    instructions = triage_instructions or DEFAULT_TRIAGE_INSTRUCTIONS
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return f"""You are an email triage assistant. Your task is to classify each email into exactly one of: ignore, notify, respond.

## Background
{background or "No specific background provided."}

When the email is from the user's Gmail inbox (incoming message just sent to them), classify whether to ignore, notify, or respond based on the content.

## Instructions
{instructions}

Today's date is {today}. You must output exactly one classification. Do not invent categories. If the content is the user asking the assistant to send an email or take an action, always classify as **respond**. Prefer notify over ignore when in doubt; prefer respond when a direct reply or action is requested."""


def get_triage_user_prompt(from_addr: str, to_addr: str, subject: str, body_or_thread: str, from_gmail_inbox: bool = False) -> str:
    """User prompt for triage: email metadata and content in a fixed format.
    When from_gmail_inbox is True, states that this email was just sent to the user's Gmail inbox."""
    inbox_note = "\n**This email just arrived in the user's Gmail inbox (incoming message).**\n" if from_gmail_inbox else ""
    return f"""## Email to classify{inbox_note}
- **From:** {from_addr}
- **To:** {to_addr}
- **Subject:** {subject}

## Body / thread
{body_or_thread}

Classify the above email into exactly one of: ignore, notify, respond. Output your reasoning and then your classification."""


# Phase 4: system prompt for the agent with tools (send email, question, done).
def get_agent_system_prompt_with_tools() -> str:
    """System prompt for response agent with send_email_tool and question/done."""
    from email_assistant.tools.gmail.prompt_templates import get_gmail_tools_prompt
    return (
        "You are a helpful assistant. You can send emails on the user's behalf and answer questions. "
        "When the user asks you to send an email to a specific address, use send_email_tool with "
        "email_address, subject, and body (do not use email_id for new emails). "
        "When replying to an email (e.g. 'reply to this email'), use send_email_tool with email_id as well. "
        "When you need clarification, use question_tool. When you have completed the request, use done_tool.\n\n"
        + get_gmail_tools_prompt()
    )


# Phase 5: response agent prompt with HITL/memory placeholders (same content as get_agent_system_prompt_with_tools for now).
def get_agent_system_prompt_hitl_memory(
    response_preferences: str = "",
    cal_preferences: str = "",
) -> str:
    """System prompt for response agent when using memory (Phase 6). Phase 5 uses same tools prompt."""
    from datetime import datetime
    from email_assistant.tools.gmail.prompt_templates import get_gmail_tools_prompt
    today = datetime.utcnow().strftime("%Y-%m-%d")
    prefs = f"\n## Response preferences\n{response_preferences}\n" if response_preferences else ""
    cal = f"\n## Calendar preferences\n{cal_preferences}\n" if cal_preferences else ""
    return (
        "You are an email assistant. You can send emails (new or reply), ask the user for clarification, and mark tasks done.\n"
        + prefs
        + cal
        + "\n"
        + get_gmail_tools_prompt()
        + f"\n\nToday's date is {today}. Do not invent recipients, events, or email content. When in doubt, use question_tool. Use done_tool when finished."
    )
