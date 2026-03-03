# 03 — Architecture and flow

How the graph is structured and how data flows from input to output.

---

## One agent, two subagents

The agent is a **single compiled graph** with two **subagents** (compiled subgraphs used as nodes):

1. **Email Assistant subagent** — Triage (ignore / notify / respond) and human-in-the-loop for **notify**. When it exits, the parent reads `classification_decision` and `_notify_choice` and routes to prepare_messages (respond) or END (ignore).
2. **Response subagent** — Chat → tools → persist_messages. Handles both **question mode** and the **respond** path after triage. Reply context is injected by **prepare_messages** before this subgraph runs.

---

## Top-level flow

```
START
  → input_router
  → if email_input present: email_assistant (subgraph)
     else: prepare_messages
  → after email_assistant: if respond or _notify_choice==respond → prepare_messages
                           else → END
  → prepare_messages → response_agent (subgraph) → mark_as_read → END
```

- **input_router:** Normalizes state; routes to **email_assistant** when `email_input` is set, otherwise to **prepare_messages** (question mode).
- **email_assistant (subgraph):** triage_router → ignore/respond → END, or notify → triage_interrupt_handler → END. The handler calls `interrupt()` so the graph pauses; on resume, `_notify_choice` is set.
- **prepare_messages:** If `email_id` and `email_input` are set, prepends a HumanMessage with reply context (and "just arrived in Gmail" when `_source == "gmail"`). Then goes to Response subgraph.
- **response_agent (subgraph):** Chat → tools → persist_messages in a loop; uses send_email_tool (new + reply), question_tool, done_tool.
- **mark_as_read:** When `email_id` is set, marks the Gmail message as read.

---

## State

- **State:** `messages`, `email_input`, `classification_decision`, `email_id`, `_notify_choice`, `user_message`, `question`.
- **StateInput:** Input can provide `email_input`, `user_message`, or `question` (and `messages`). Used for typing and validation.

---

## Email Assistant subgraph (inside)

- **START → triage_router** (one LLM call with `RouterSchema`: ignore / notify / respond).
- **Conditional:** if **notify** → triage_interrupt_handler (calls `interrupt()`, then returns `_notify_choice`); else → END.
- **triage_interrupt_handler → END** (parent graph uses `_notify_choice` to route).

---

## Response subgraph (inside)

- **START → chat** (LLM with tools) → conditional: if tool calls → run tools, append results, loop back to chat; else → **persist_messages → END**.
- Uses full `State`; nodes read/write `messages`. Built by `simple_agent.build_response_subgraph()`.

---

## Related docs

- **04_EMAIL_TRIAGE_AND_HITL.md** — Triage categories and notify interrupt/resume.
- **05_DATABASE_AND_PERSISTENCE.md** — Checkpointer, store, and app tables.
