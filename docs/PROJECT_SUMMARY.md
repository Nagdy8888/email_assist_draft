# Project summary: from start to now

Summary of what has been done from the beginning of the Email Assistant project until now.

---

## 1. Project purpose and stack

**Email Assistant** is a LangGraph-based agent that:

- **Processes emails** — Triage (ignore / notify / respond). When classification is **notify**, the graph **pauses** (interrupt) and asks you whether to respond or ignore; resume with Command(resume="respond") or Command(resume="ignore").
- **Answers questions** — Direct user questions (no triage), with optional tools.
- **Sends email** — Reply to triaged email or send a new email to a given address on request.

**Tech stack:** LangGraph, LangChain, OpenAI, Postgres/Supabase (checkpointer, store, and app tables in `email_assistant` schema), Gmail API, optional Google Calendar. Optional LangSmith for tracing.

---

## 2. Phased implementation (Phases 1–7)

The work followed a **seven-phase plan** (see `.cursor/plans/email_agent_phased_implementation_d99ca526.plan.md`).

| Phase | Done | Description |
|-------|------|-------------|
| **Phase 1** | ✅ | All dependencies and full project structure. `pyproject.toml`, `src/email_assistant/`, nodes/tools/db stubs, `.env.example`, migrations folder. |
| **Phase 2** | ✅ | Simple agent: user message → LLM response. In-memory or Postgres checkpointer. |
| **Phase 3** | ✅ | Supabase/Postgres: app tables (`migrations/001_email_assistant_tables.sql`), checkpointer, store. Messages persisted when `DATABASE_URL` is set. `scripts/setup_db.py`, `db/checkpointer.py`, `db/store.py`, `db/persist_messages.py`. |
| **Phase 4** | ✅ | Send email: `send_email_tool` (new email + reply by `email_id`), `question_tool`, `done_tool`. Gmail OAuth (`.secrets/credentials.json`, `.secrets/token.json`). Tool loop: chat → tools → persist_messages. |
| **Phase 5** | ✅ | Email mode + triage. Input: `email_input` (triage path) or `user_message` / `question` (question path). **input_router** → triage_router or response_agent. **triage_router** (LLM + RouterSchema): ignore / notify / respond. **notify** path: graph **pauses** (interrupt()); user resumes with Command(resume="respond") or Command(resume="ignore"). **respond** path: response_agent + **mark_as_read**. |
| **Phase 6** | (partial) | Memory and HITL: prompts and structure in place; store/checkpointer used where applicable. |
| **Phase 7** | ✅ | Run script, notebook placeholder, and documentation. `scripts/run_agent.py`, `docs/` (ARCHITECTURE, CONFIGURATION, DATABASE, FILES_AND_MODULES, PROMPTS, RUNNING_AND_TESTING, PROJECT_OVERVIEW). |

---

## 3. Single graph with two subagents (refactor)

A later refactor (see `.cursor/plans/single_graph_two_subagents.plan.md`) unified everything into **one top-level graph** with **two subagents** as nodes:

- **Email Assistant subagent** — Compiled subgraph: triage_router → (ignore/respond → END, notify → triage_interrupt_handler → END). The notify handler calls **interrupt()** so the graph pauses; the user chooses respond or ignore and resumes with Command(resume=...). Parent routes using `classification_decision` and `_notify_choice`.
- **Response subagent** — Compiled subgraph: chat → tools → persist_messages (same tool loop as before).
- **prepare_messages** — Node that injects reply context when `email_id` / `email_input` are set, then goes to the Response subgraph.
- **Single entry** — `langgraph.json` exposes only `email_assistant` (from `email_assistant_hitl_memory_gmail.py`). Question mode = invoke with `user_message` and no `email_input`.

**State:** `State` includes `user_message`, `question`, `email_input`, `classification_decision`, `email_id`, `_notify_choice`, `messages`. Input schema: `StateInput`. Single checkpointer for the whole graph.

**Flow:** START → input_router → (email_input → email_assistant subgraph **or** prepare_messages) → after email_assistant, route to prepare_messages or END → prepare_messages → response_agent subgraph → mark_as_read → END.

---

## 4. Gmail automatic ingestion

So the agent can **see real Gmail inbox messages** without manual input:

- **`src/email_assistant/tools/gmail/fetch_emails.py`** — `list_inbox_message_ids()`, `get_message_as_email_input()`, `fetch_recent_inbox()`. Uses Gmail API to list and fetch messages in `email_input` shape.
- **`scripts/watch_gmail.py`** — Polls Gmail (default: unread INBOX every 60s), invokes the graph with each new message, stores processed ids in `.gmail_processed_ids.json` so each email is handled once. Run in a **second terminal** while `langgraph dev` runs in the first (Studio + watcher together).
- **`scripts/test_gmail_read.py`** — Tests Gmail read access (OAuth + list + get one message). Use before relying on the watcher.

**Env (optional):** `GMAIL_POLL_INTERVAL`, `GMAIL_UNREAD_ONLY`, `GMAIL_MAX_RESULTS`, `GMAIL_PROCESSED_IDS_FILE`. See CONFIGURATION.md.

---

## 5. “Incoming Gmail” awareness

So the agent knows when a message **just arrived in Gmail**:

- **input_router** — When normalizing `email_input`, sets `_source: "gmail"` when the payload has a Gmail message id or Gmail API structure.
- **Triage** — `get_triage_user_prompt(..., from_gmail_inbox=True)` adds: “This email just arrived in the user's Gmail inbox.”
- **prepare_messages** — When `email_input._source == "gmail"`, reply context includes: “This email just arrived in the user's Gmail inbox.”

---

## 6. Checkpointer and store in email_assistant schema and Studio

- **CLI checkpointer** — [checkpointer.py](src/email_assistant/db/checkpointer.py) uses a raw Postgres connection with `SET search_path TO email_assistant`, so all checkpoint tables (`checkpoint_migrations`, `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`) live in the **email_assistant** schema (same as app tables). Run `scripts/setup_db.py` once; use `prepare_threshold=None` to avoid DuplicatePreparedStatement with Supabase pooled connections.
- **Store** — [store.py](src/email_assistant/db/store.py) creates the LangGraph store tables (`store`, `store_migrations`) in the **email_assistant** schema via the same pattern: dedicated connection with `prepare_threshold=None` and `SET search_path TO email_assistant`. `setup_store()` is called from `scripts/setup_db.py`; at runtime `postgres_store()` uses the same connection settings so the store and checkpointer coexist without prepared-statement conflicts.
- **Studio checkpointer** — [studio_checkpointer.py](src/email_assistant/db/studio_checkpointer.py) provides an async context manager; [langgraph.json](langgraph.json) has `"checkpointer": {"path": "...:generate_checkpointer"}`. When `DATABASE_URL` is set, Studio uses the same Supabase Postgres in the `email_assistant` schema.
- **created_at** — Migration [002_checkpoint_created_at.sql](migrations/002_checkpoint_created_at.sql) adds `created_at TIMESTAMPTZ` to all checkpoint tables; `setup_db.py` runs it after `cp.setup()`.

---

## 7. Mock emails and simulation

- **Fixtures** — [fixtures/mock_emails.py](src/email_assistant/fixtures/mock_emails.py): `MOCK_EMAIL_NOTIFY`, `MOCK_EMAIL_RESPOND`, `MOCK_EMAIL_IGNORE`, `get_mock_email(name)`. Used for testing triage and full flow without Gmail API.
- **run_mock_email.py** — Runs the graph with a mock email; on notify interrupt prompts (r)espond or (i)gnore and resumes with Command(resume=...). Uses Postgres checkpointer when `DATABASE_URL` is set, else MemorySaver.
- **simulate_gmail_email.py** — Simulates the graph receiving a real Gmail-style email: prints steps (triage, notify choice), same payload shape as the watcher would pass. Use `SIMULATE_EMAIL=notify|respond|ignore` or CLI arg.

---

## 8. Triage and Studio fixes

- **Triage “send to Gmail”** — Triage was classifying user requests like “send message to Gmail” as **ignore**. Prompts updated so that when the content is the user asking to send an email or take an action, classification is **respond**.
- **LangGraph Studio** — The API injects the checkpointer from `langgraph.json` when `checkpointer.path` is set. The entry point `email_assistant` is built with no checkpointer in code; `run_agent.py` and the watcher pass an explicit checkpointer (MemorySaver or Postgres). Set `DATABASE_URL` so Studio uses Supabase (same as CLI).
- **Gmail 403 / read scope** — If the graph “can’t read” emails, the token often lacks `gmail.readonly`. Delete (or rename) `.secrets/token.json` and run `test_gmail_read.py` to re-run OAuth and grant read (and modify) scope. Doc: RUNNING_AND_TESTING.md.

---

## 9. What you can do today

| Action | How |
|--------|-----|
| **Question mode** | Invoke with `{"user_message": "Hello"}` or run `run_agent.py` (default message or `RUN_MESSAGE`). |
| **Email mode (manual)** | Invoke with `{"email_input": {"from", "to", "subject", "body", "id"}}` or run `run_agent.py` with `RUN_EMAIL_*` env vars. |
| **Mock email / simulation** | `uv run python scripts/run_mock_email.py` or `uv run python scripts/simulate_gmail_email.py` (fixture: notify/respond/ignore). No Gmail API; notify path **pauses** and prompts you to choose respond or ignore. |
| **Automatic Gmail** | Run `uv run python scripts/watch_gmail.py` in a second terminal (Terminal 1: `uv run langgraph dev` for Studio). |
| **LangGraph Studio** | `uv run langgraph dev`, open Studio URL. Single graph **email_assistant**; question or email input. When classification is **notify**, the graph pauses (interrupt); use Studio’s resume UI to send "respond" or "ignore". Set `DATABASE_URL` so Studio uses Supabase checkpointer in `email_assistant` schema. |
| **Persist messages** | Set `DATABASE_URL`, run migrations and `setup_db.py`; run script and watcher use Postgres checkpointer (email_assistant schema) and persist messages. |

---

## 10. Key files (short)

| Area | Files |
|------|--------|
| **Entry / graph** | `email_assistant_hitl_memory_gmail.py` (build_email_assistant_graph, email_assistant), `langgraph.json` |
| **Subgraphs** | `simple_agent.py` (build_response_subgraph), triage in same entry file |
| **Nodes** | `nodes/input_router.py`, `nodes/triage.py`, `nodes/triage_interrupt.py` (interrupt() for notify — user chooses respond/ignore), `nodes/prepare_messages.py`, `nodes/mark_as_read.py` |
| **State** | `schemas.py` (State, StateInput, RouterSchema, NotifyChoiceSchema) |
| **Checkpointer / store** | `db/checkpointer.py` (sync, search_path=email_assistant), `db/studio_checkpointer.py` (async for Studio), `db/store.py` (PostgresStore in email_assistant schema, prepare_threshold=None) |
| **Gmail** | `tools/gmail/auth.py`, `send_email.py`, `mark_as_read.py`, `fetch_emails.py` |
| **Fixtures / scripts** | `fixtures/mock_emails.py`, `run_agent.py`, `run_mock_email.py`, `simulate_gmail_email.py`, `watch_gmail.py`, `test_gmail_read.py`, `setup_db.py` |
| **Migrations** | `001_email_assistant_tables.sql`, `002_checkpoint_created_at.sql` |
| **Docs** | `docs/ARCHITECTURE.md`, `docs/RUNNING_AND_TESTING.md`, `docs/CONFIGURATION.md`, `docs/FILES_AND_MODULES.md`, `docs/PROMPTS.md`, `docs/DATABASE.md`, `docs/PROJECT_OVERVIEW.md` |

---

*Summary generated from the phased plan, single-graph refactor, checkpointer/store schema work, mock emails, and current docs. For full detail, see the plan files under `.cursor/plans/` and the docs under `docs/`.*
