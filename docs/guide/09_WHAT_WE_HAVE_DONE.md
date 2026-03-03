# 09 — What we have done till now

Summary of what has been implemented from project start to now: phases, refactors, and features.

---

## 1. Phased implementation (Phases 1–7)

| Phase | Status | What was done |
|-------|--------|----------------|
| **Phase 1** | Done | Dependencies and full project structure: `pyproject.toml`, `src/email_assistant/`, nodes/tools/db stubs, `.env.example`, migrations folder. |
| **Phase 2** | Done | Simple agent: user message → LLM response. In-memory or Postgres checkpointer. |
| **Phase 3** | Done | Supabase/Postgres: app tables (`001_email_assistant_tables.sql`), checkpointer, store. Messages persisted when `DATABASE_URL` is set. `setup_db.py`, `checkpointer.py`, `store.py`, `persist_messages.py`. |
| **Phase 4** | Done | Send email: `send_email_tool` (new + reply by `email_id`), `question_tool`, `done_tool`. Gmail OAuth. Tool loop: chat → tools → persist_messages. |
| **Phase 5** | Done | Email mode + triage. **input_router** → triage_router or prepare_messages. **triage_router** (LLM + RouterSchema): ignore / notify / respond. **notify** path: graph **pauses** (interrupt()); user resumes with Command(resume="respond") or Command(resume="ignore"). **respond** path: response_agent + **mark_as_read**. |
| **Phase 6** | Partial | Memory and HITL: prompts and structure in place; store/checkpointer used where applicable. |
| **Phase 7** | Done | Run script, notebook placeholder, documentation. |

---

## 2. Single graph with two subagents (refactor)

Everything was unified into **one top-level graph** with **two subagents**:

- **Email Assistant subagent:** triage_router → (ignore/respond → END, notify → triage_interrupt_handler → END). Notify uses **interrupt()**; user chooses respond or ignore and resumes with Command(resume=...).
- **Response subagent:** chat → tools → persist_messages.
- **prepare_messages** injects reply context when `email_id`/`email_input` are set.
- **langgraph.json** exposes only **email_assistant** (from `email_assistant_hitl_memory_gmail.py`).

---

## 3. Gmail and mock emails

- **Gmail:** `fetch_emails.py` (list_inbox_message_ids, get_message_as_email_input); **watch_gmail.py** polls INBOX and invokes the graph per new message; **test_gmail_read.py** tests OAuth and read.
- **input_router** sets **`_source: "gmail"`** when the payload has a Gmail id or Gmail API structure; triage and prepare_messages use this for "just arrived in Gmail" context.
- **Mock emails:** MOCK_EMAIL_NOTIFY, MOCK_EMAIL_RESPOND, MOCK_EMAIL_IGNORE in `fixtures/mock_emails.py`. **run_mock_email.py** and **simulate_gmail_email.py** use them for testing without Gmail API.

---

## 4. Checkpointer and store in email_assistant schema

- **CLI checkpointer** (`checkpointer.py`): Postgres connection with **search_path = email_assistant** and **prepare_threshold=None** (avoids DuplicatePreparedStatement with Supabase). Tables created by `setup_db.py`.
- **Studio checkpointer** (`studio_checkpointer.py`): Async context manager; `langgraph.json` points to it. Same schema and Supabase-friendly options.
- **Store** (`store.py`): PostgresStore in email_assistant schema with **prepare_threshold=None**; `setup_store()` and `postgres_store()`.
- **Migration 002:** Adds **created_at** to checkpoint tables; `setup_db.py` runs it after `cp.setup()`.

---

## 5. Triage and Studio fixes

- **Triage "send me the report":** Prompts updated so emails asking for a reply/document/action are **respond**. **`_is_explicit_request()`** in triage.py forces **respond** for phrases like "send me the report", "could you send", "by Friday".
- **Double-wrapped email_input:** input_router unwraps **`{"email_input": {"email_input": {...}}}`** so Studio payloads keep from/to/subject/body.
- **HITL on notify:** Notify path uses **interrupt()**; run_agent.py and run_mock_email.py prompt (r)espond/(i)gnore and resume with Command(resume=...). Studio resume UI sends "respond" or "ignore".
- **Store setup DuplicatePreparedStatement:** store uses a dedicated connection with **prepare_threshold=None** so setup_db.py completes without error.

---

## 6. Scripts and debugging

- **run_agent.py** — Question or email mode; on notify interrupt, prompts and resumes.
- **run_mock_email.py** — Mock email (notify/respond/ignore); on notify, prompts and resumes.
- **simulate_gmail_email.py** — Simulate Gmail flow with mock payload.
- **watch_gmail.py** — Poll Gmail, invoke graph per new email.
- **setup_db.py** — One-time: checkpointer, migration 002, store.
- **debug_triage.py** — Local triage debug (input_router + triage_router; optional payload file).

---

## 7. Documentation

- **docs/** — ARCHITECTURE, CONFIGURATION, DATABASE, FILES_AND_MODULES, PROMPTS, RUNNING_AND_TESTING, PROJECT_OVERVIEW, PROJECT_SUMMARY.
- **docs/guide/** — This set (01_OVERVIEW through 10_QUICK_REFERENCE + DOCS_INDEX) for a structured guide.

---

*For the phased plan files, see `.cursor/plans/`. For a short "what you can do today" and key files, see **../PROJECT_SUMMARY.md** and **10_QUICK_REFERENCE.md**.*
