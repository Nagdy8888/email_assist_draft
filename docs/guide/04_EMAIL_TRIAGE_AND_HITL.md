# 04 — Email triage and human-in-the-loop

How triage classifies emails and how the notify path pauses for your choice.

---

## Triage categories

Each email is classified into exactly one of:

| Category | Meaning | What happens |
|----------|---------|--------------|
| **ignore** | Low value or noise (e.g. newsletters, receipts). | Graph ends; no reply, no prompt. |
| **notify** | FYI — user should see it but no reply required (e.g. deploy done, reminders). | Graph **pauses** (interrupt); you choose **respond** or **ignore**; then graph continues or ends. |
| **respond** | Needs a reply or action (e.g. "send me the report", questions, requests). | Graph runs **prepare_messages → response_agent → mark_as_read** so the agent can reply. |

---

## How triage runs

1. **input_router** normalizes `email_input` (and unwraps double-nested payloads from Studio).
2. **triage_router** (in `nodes/triage.py`):
   - If subject/body match explicit request phrases ("send me the report", "could you send", "by Friday", etc.), classification is forced to **respond** without calling the LLM.
   - Otherwise, one LLM call with **RouterSchema** (reasoning + classification). System and user prompts are from `prompts.py` (DEFAULT_TRIAGE_INSTRUCTIONS, get_triage_system_prompt, get_triage_user_prompt).

---

## Notify path: human-in-the-loop (HITL)

When the classification is **notify**:

1. The graph goes to **triage_interrupt_handler**.
2. The handler calls **`interrupt(NOTIFY_INTERRUPT_MESSAGE)`**. Execution pauses; state is saved by the checkpointer.
3. The caller (CLI or Studio) sees **`__interrupt__`** in the result and can prompt you: "Respond or ignore?"
4. You resume by invoking again with **`Command(resume="respond")`** or **`Command(resume="ignore")`** and the same `thread_id` (and checkpointer).
5. The resume value becomes the return value of `interrupt()`; the handler writes **`_notify_choice`** and returns. The parent graph then routes: **respond** → prepare_messages; **ignore** → END.

**Requirement:** A **checkpointer** (Postgres or MemorySaver) is required for interrupt/resume; the graph state is persisted at the interrupt point.

---

## Mock emails for testing

In `fixtures/mock_emails.py`:

- **MOCK_EMAIL_NOTIFY** — FYI style; likely classified as notify (triggers HITL).
- **MOCK_EMAIL_RESPOND** — "Can you send me the report by Friday?" → respond (and matches explicit-request override).
- **MOCK_EMAIL_IGNORE** — Newsletter style; likely ignore.

Use with `run_mock_email.py` or as run input in Studio.

---

## Related docs

- **03_ARCHITECTURE_AND_FLOW.md** — Where triage and triage_interrupt_handler sit in the graph.
- **07_PROMPTS_AND_SCHEMAS.md** — Triage prompts and RouterSchema.
- **08_RUNNING_AND_TESTING.md** — How to run and resume in CLI and Studio.
