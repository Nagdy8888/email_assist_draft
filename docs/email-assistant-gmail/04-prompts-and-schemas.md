# Prompts and Schemas

This document summarizes the **prompts** and **schemas** used by the Gmail email assistant agent.

---

## 1. Schemas

### `RouterSchema` (triage output)

Used by `llm_router = llm.with_structured_output(RouterSchema)` so triage returns a fixed shape:

- **reasoning** (`str`): Step-by-step reasoning for the classification.
- **classification** (`Literal["ignore", "respond", "notify"]`):
  - **ignore**: Not worth responding to or tracking.
  - **notify**: Important to know about but no reply needed.
  - **respond**: Needs a direct reply.

### `StateInput`

TypedDict for graph input:

- **email_input** (`dict`): The raw email. Can be Gmail format (`from`, `to`, `subject`, `body`, `id`), mock/Studio format (`author`, `to`, `subject`, `email_thread`), or message-style (`content`, optional `to`, `subject`; see `parse_gmail` in `utils.py`).

### `State`

Extends **MessagesState** (adds `messages`) with:

- **email_input** (`dict`): Same as in StateInput; carried through the run.
- **classification_decision** (`Literal["ignore", "respond", "notify"]`): Set by `triage_router`, used in triage interrupt handler for the interrupt action label.

### `UserPreferences` (memory update output)

Used by the memory-update LLM (e.g. `llm.with_structured_output(UserPreferences)`):

- **chain_of_thought** (`str`): Reasoning about what to add/change in the profile.
- **user_preferences** (`str`): The updated profile text stored under `"user_preferences"` in the store.

---

## 2. Triage Prompts

### `triage_system_prompt`

Template with placeholders:

- **{background}**: e.g. `default_background` (“I'm Lance, a software engineer at LangChain.”).
- **{triage_instructions}**: From memory (`get_memory(..., "triage_preferences", default_triage_instructions)`).

Content: role (triage emails), background, instructions (categorize into IGNORE / NOTIFY / RESPOND), and rules (the triage_instructions).

### `triage_user_prompt`

Template:

- **{author}**, **{to}**, **{subject}**, **{email_thread}**: From `parse_gmail(state["email_input"])`.

Asks to “determine how to handle the below email thread” with From/To/Subject and thread content.

---

## 3. Agent (Response) Prompt

### `agent_system_prompt_hitl_memory`

Used in `llm_call` with:

- **{tools_prompt}**: `GMAIL_TOOLS_PROMPT` (list of Gmail tools: fetch_emails, send_email, check_calendar, schedule_meeting, triage_email, Done).
- **{background}**: `default_background`.
- **{response_preferences}**: From `get_memory(..., "response_preferences", default_response_preferences)`.
- **{cal_preferences}**: From `get_memory(..., "cal_preferences", default_cal_preferences)`.

Instructions stress: analyze email, call one tool at a time, use Question when context is missing, use write_email/send_email for replies, check_calendar then schedule_meeting for meetings, then write_email and Done. Also includes today’s date for scheduling.

---

## 4. Default Memory Content

### `default_background`

Short identity line, e.g. “I'm Lance, a software engineer at LangChain.”

### `default_response_preferences`

Guidance on tone (professional, concise), deadlines, technical questions, event/conference invites, collaboration and meeting scheduling (e.g. verify calendar, propose multiple times, mention duration and purpose).

### `default_cal_preferences`

E.g. “30 minute meetings are preferred, but 15 minute meetings are also acceptable.”

### `default_triage_instructions`

Bullet lists of:

- What to **ignore**: marketing, spam, FYI with no direct questions, etc.
- What to **notify**: team out sick, build/deploy notices, status updates, announcements, FYI relevant to projects, HR deadlines, renewals, GitHub notifications.
- What to **respond** to: direct questions, meeting requests, critical bugs, management requests, client inquiries, technical/docs/API questions, family/personal reminders.

---

## 5. Memory Update Prompts

### `MEMORY_UPDATE_INSTRUCTIONS`

System instructions for the memory-update LLM:

- Role: update user preferences from HITL feedback only where relevant.
- Rules: never overwrite entire profile; only add or correct specific facts; preserve rest and format.
- Steps: analyze current profile, review feedback messages, extract preferences, compare, identify changes, output full updated profile.
- Includes an example (moving “system admin notifications” from RESPOND to NOTIFY).
- Placeholders: **{current_profile}**, **{namespace}** (for context in the prompt).

### `MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT`

Short reminder appended when updating from HITL: same rules (no full overwrite, targeted updates only, preserve rest, consistent format, output string).

---

## 6. Gmail Tools Prompt

### `GMAIL_TOOLS_PROMPT`

Numbered list of tools and signatures:

1. fetch_emails_tool(email_address, minutes_since)
2. send_email_tool(email_id, response_text, email_address, additional_recipients)
3. check_calendar_tool(dates)
4. schedule_meeting_tool(attendees, title, start_time, end_time, organizer_email, timezone)
5. triage_email(ignore, notify, respond)
6. Done

This is what the response agent sees as its tool list text; the actual tools bound to the LLM in this graph are send_email_tool, schedule_meeting_tool, check_calendar_tool, Question, and Done (no fetch_emails_tool or triage_email in the bound list).

---

## 7. Utils Used for Display and Parsing

- **parse_gmail(email_input)**: Returns `(author, to, subject, email_thread, email_id)`. Handles Gmail, mock/Studio, and message-style inputs; see `utils.py`.
- **format_gmail_markdown(subject, author, to, email_thread, email_id)**: Produces markdown for the email (with optional ID); converts HTML body to text if needed.
- **format_for_display(tool_call)**: Produces readable markdown for Agent Inbox for write_email, schedule_meeting, Question, or generic tool args. (For Gmail tools send_email_tool / schedule_meeting_tool, the generic branch is used and shows JSON args.)

All prompts and default content are defined in `src/email_assistant/prompts.py`; schemas in `src/email_assistant/schemas.py`; Gmail tool prompt in `src/email_assistant/tools/gmail/prompt_templates.py`.
