# Prompts

Where prompts live and what they do.

## Phase 2

- **`prompts.SIMPLE_AGENT_SYSTEM_PROMPT`** — System prompt for the simple Q&A agent (one node, no tools).

## Phase 4

- **`prompts.get_agent_system_prompt_with_tools()`** — System prompt for the agent with tools: send_email_tool, question_tool, done_tool; instructs "send email to X" → use send_email_tool with email_address, subject, body; reply with email_id when replying.
- **`tools/gmail/prompt_templates.get_gmail_tools_prompt()`** — Tools section with today's date and tool descriptions (GMAIL_TOOLS_PROMPT); mentions reply with email_id.

## Phase 5: Triage and response agent

- **`prompts.DEFAULT_TRIAGE_INSTRUCTIONS`** — Default bullet list for ignore / notify / respond with examples. Instructs triage to classify as **respond** when the user is asking to send an email or take an action (e.g. "send to Gmail") so the response agent can run.
- **`prompts.get_triage_system_prompt(background=..., triage_instructions=...)`** — System prompt for triage router LLM; starts with **CRITICAL** rule that any email asking the recipient to send something or reply must be classified as **respond**; injects background, triage_instructions, and today's date.
- **`prompts.get_triage_user_prompt(..., from_gmail_inbox=...)`** — User prompt for triage: email metadata and body; when `from_gmail_inbox` is True (email has Gmail id or API structure), states that the email just arrived in the user's Gmail inbox.
- **`prompts.get_agent_system_prompt_hitl_memory(response_preferences=..., cal_preferences=...)`** — Response agent system prompt with optional memory sections (Phase 6); Phase 5 uses same tools prompt and today's date.
