# 07 — Prompts and schemas

Where prompts live and how triage/response state and outputs are shaped.

---

## Prompts (prompts.py)

| Prompt / constant | Use |
|-------------------|-----|
| **SIMPLE_AGENT_SYSTEM_PROMPT** | Simple Q&A agent (Phase 2). |
| **DEFAULT_TRIAGE_INSTRUCTIONS** | Bullet list for ignore / notify / respond with examples; instructs "respond" when the email asks for a reply, document, or action. |
| **get_triage_system_prompt(background, triage_instructions)** | Full system prompt for triage LLM; includes CRITICAL rule for "send me the report" style → respond. |
| **get_triage_user_prompt(from_addr, to_addr, subject, body_or_thread, from_gmail_inbox)** | User prompt for triage: email metadata and body; optional "just arrived in Gmail inbox" note. |
| **NOTIFY_CHOICE_SYSTEM** | System prompt for the notify auto-decision (currently unused; notify path uses interrupt instead). |
| **get_notify_choice_user_prompt(from_addr, subject, body_snippet)** | User prompt for notify choice (unused when using interrupt). |
| **get_agent_system_prompt_with_tools()** | Response agent: send email, question, done; mentions reply with email_id. |
| **get_agent_system_prompt_hitl_memory(response_preferences, cal_preferences)** | Response agent with optional memory sections (Phase 6). |

Gmail tools text is in **tools/gmail/prompt_templates.py** (get_gmail_tools_prompt, GMAIL_TOOLS_PROMPT).

---

## Schemas (schemas.py)

### State and input

| Type | Purpose |
|------|--------|
| **State** | Full graph state: `messages`, `email_input`, `classification_decision`, `email_id`, `_notify_choice`, `user_message`, `question`. |
| **StateInput** | Input schema: `messages`, `email_input`, `user_message`, `question` (all optional). |
| **MessagesState** | Minimal state with only `messages` (add_messages). |

### Structured outputs

| Type | Purpose |
|------|--------|
| **ClassificationDecision** | Literal `"ignore" \| "notify" \| "respond"`. |
| **RouterSchema** | Triage LLM output: `reasoning`, `classification` (ClassificationDecision). |
| **NotifyChoiceSchema** | Notify choice output: `choice` ("respond" \| "ignore") — used when not using interrupt. |

---

## Triage override (triage.py)

**`_is_explicit_request(subject, body)`** returns True when the email clearly asks for a reply or document (e.g. "send me the report", "could you send", "by Friday"). When True, **triage_router** returns **respond** without calling the LLM, so "send me the report" style emails are always classified as respond.

---

## Related docs

- **04_EMAIL_TRIAGE_AND_HITL.md** — How triage and notify HITL work.
- **../PROMPTS.md** — Full prompt reference.
