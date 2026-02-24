# Triage and Memory

This document details the **triage router**, the **triage interrupt handler** (notify path), and the **memory** helpers used across the agent.

---

## 1. Triage Router (`triage_router`)

### Purpose

Decide how to handle each incoming email: **ignore**, **notify**, or **respond**. This avoids wasting time on spam, newsletters, and non-actionable mail, and surfaces important-but-no-reply-needed items as notifications.

### Steps

1. **Parse input**  
   `author, to, subject, email_thread, email_id = parse_gmail(state["email_input"])`. Supports Gmail API format (`from`, `to`, `subject`, `body`, `id`), mock/Studio format (`author`, `to`, `subject`, `email_thread`), and message-style content.

2. **Build user prompt**  
   `triage_user_prompt.format(author=..., to=..., subject=..., email_thread=...)` — “Please determine how to handle the below email thread: …”.

3. **Load triage memory**  
   `triage_instructions = get_memory(store, ("email_assistant", "triage_preferences"), default_triage_instructions)`.

4. **Build system prompt**  
   `triage_system_prompt.format(background=default_background, triage_instructions=triage_instructions)`.

5. **Call router LLM**  
   `llm_router.invoke([system, user])` where `llm_router = llm.with_structured_output(RouterSchema)`. Result has `classification` and `reasoning`.

6. **Return Command**  
   - **respond**: `Command(goto="response_agent", update={classification_decision, messages: ["Respond to the email: " + email_markdown]})`.  
   - **ignore**: `Command(goto=END, update={classification_decision})`.  
   - **notify**: `Command(goto="triage_interrupt_handler", update={classification_decision})`.

`email_markdown` is produced by `format_gmail_markdown(subject, author, to, email_thread, email_id)` for use in the Agent Inbox and in the response agent.

---

## 2. Triage Interrupt Handler (`triage_interrupt_handler`)

### Purpose

Used only when triage classified the email as **notify**. It shows the email in the **Agent Inbox** and lets the user choose: **respond** (with optional feedback) or **ignore**. The choice is used to update triage memory.

### Steps

1. **Parse and format**  
   Same `parse_gmail` and `format_gmail_markdown` as in the router.

2. **Build interrupt request**  
   - `action_request`: `{"action": "Email Assistant: notify", "args": {}}`.  
   - `config`: `allow_ignore=True`, `allow_respond=True`, `allow_edit=False`, `allow_accept=False`.  
   - `description`: `email_markdown`.

3. **Interrupt**  
   `response = interrupt([request])[0]`.

4. **Handle response**  
   - **response**: User wants to reply. Append feedback to `messages` (“User wants to reply … Use this feedback to respond: {user_input}”), call `update_memory(store, ("email_assistant", "triage_preferences"), ...)` with the decision and messages, then `Command(goto="response_agent", update={messages})`.  
   - **ignore**: Append a note that the user ignored the email, call `update_memory(..., triage_preferences, ...)` with that context, then `Command(goto=END, update={messages})`.

So: **notify** always goes through human review; the human’s choice (respond vs ignore) is written into triage preferences for future emails.

---

## 3. Memory: `get_memory` and `update_memory`

### Namespaces

- **`("email_assistant", "triage_preferences")`** — What to ignore / notify / respond to; updated from triage and from notify-path choices (and from HITL “ignore” on drafts/questions).  
- **`("email_assistant", "response_preferences")`** — How to write emails; updated when the user edits or gives feedback on the send_email_tool.  
- **`("email_assistant", "cal_preferences")`** — How to schedule meetings; updated when the user edits or gives feedback on the schedule_meeting_tool.

All are stored under the key **`"user_preferences"`** in the LangGraph store.

### `get_memory(store, namespace, default_content=None)`

- **Behavior**: `store.get(namespace, "user_preferences")`. If a value exists, return it; otherwise `store.put(namespace, "user_preferences", default_content)` and return `default_content`.  
- **Usage**: Triage uses it for `triage_preferences`; the response agent’s `llm_call` uses it for `cal_preferences` and `response_preferences` when building the system prompt.

### `update_memory(store, namespace, messages)`

- **Behavior**:  
  1. Get current profile: `user_preferences = store.get(namespace, "user_preferences")`.  
  2. Call an LLM with `MEMORY_UPDATE_INSTRUCTIONS.format(current_profile=..., namespace=...)` and the given `messages`, using `UserPreferences` structured output.  
  3. Save: `store.put(namespace, "user_preferences", result.user_preferences)`.

- **Rules** (from prompts): Only targeted additions or corrections; never overwrite the entire profile; preserve existing style and content.

**Reinforcement**: When updating from HITL (e.g. edits or feedback), the code often appends `MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT` so the LLM again stresses “targeted updates only.”

---

## 4. Where Memory Is Updated

| Event | Namespace | Trigger |
|-------|-----------|--------|
| User chose to **respond** to a notify email | `triage_preferences` | `triage_interrupt_handler` (response branch). |
| User chose to **ignore** a notify email | `triage_preferences` | `triage_interrupt_handler` (ignore branch). |
| User **edited** send_email_tool | `response_preferences` | `interrupt_handler` (edit branch for send_email_tool). |
| User **edited** schedule_meeting_tool | `cal_preferences` | `interrupt_handler` (edit branch for schedule_meeting_tool). |
| User **ignored** email/meeting/question draft | `triage_preferences` | `interrupt_handler` (ignore branch for send_email_tool, schedule_meeting_tool, Question). |
| User gave **feedback** (response) on send_email_tool | `response_preferences` | `interrupt_handler` (response branch). |
| User gave **feedback** on schedule_meeting_tool | `cal_preferences` | `interrupt_handler` (response branch). |

This keeps triage, response style, and calendar behavior aligned with user behavior over time.
