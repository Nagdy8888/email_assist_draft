# Prompts

Where prompts live and what they do.

## Phase 2

- **`prompts.SIMPLE_AGENT_SYSTEM_PROMPT`** — System prompt for the simple Q&A agent (one node, no tools).

## Phase 4

- **`prompts.get_agent_system_prompt_with_tools()`** — System prompt for the agent with tools: send_email_tool, question_tool, done_tool; instructs "send email to X" → use send_email_tool with email_address, subject, body.
- **`tools/gmail/prompt_templates.get_gmail_tools_prompt()`** — Tools section with today's date and tool descriptions (GMAIL_TOOLS_PROMPT).

Triage prompts are added in Phase 5 (`prompts.py` and `tools/gmail/prompt_templates.py`).
