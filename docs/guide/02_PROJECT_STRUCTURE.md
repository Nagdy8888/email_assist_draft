# 02 — Project structure and file usage

Directory layout and the role of each important file and folder.

---

## Top-level layout

```
email_assist_draft/
├── src/email_assistant/     # Main package (graph, nodes, tools, db)
├── scripts/                 # Run, mock, watcher, setup_db, debug
├── migrations/              # SQL for app + checkpoint schema
├── docs/                    # Documentation
│   ├── guide/               # This set (01–10 + DOCS_INDEX)
│   └── ...                  # ARCHITECTURE, CONFIGURATION, etc.
├── notebooks/               # Notebook placeholder (Phase 7)
├── tests/                   # Tests
├── .env.example             # Env var template
├── .env                     # Local env (do not commit)
├── langgraph.json           # Studio config (graphs, checkpointer path)
├── pyproject.toml           # Dependencies and package config
└── README.md                # Project readme
```

---

## Source package: `src/email_assistant/`


| File / folder                          | Purpose                                                                                                                                                          |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `__init__.py`                          | Package init, version; re-exports db helpers.                                                                                                                    |
| `email_assistant_hitl_memory_gmail.py` | **Entry point.** Builds and compiles the top-level graph (`build_email_assistant_graph`, `email_assistant`). Used by Studio and CLI.                             |
| `simple_agent.py`                      | Builds the **Response subgraph**: chat → tools → persist_messages. Alias `build_simple_graph`.                                                                   |
| `schemas.py`                           | **State:** `State`, `StateInput`. **Structured outputs:** `RouterSchema` (triage), `NotifyChoiceSchema`.                                                         |
| `prompts.py`                           | System/user prompts: triage, notify choice, response agent, tools. Default triage instructions.                                                                  |
| **nodes/**                             |                                                                                                                                                                  |
| `nodes/input_router.py`                | First node: normalizes input; routes by `email_input` vs `user_message`/`question`. Unwraps double-nested `email_input`; sets `_source='gmail'` when from Gmail. |
| `nodes/triage.py`                      | **triage_router:** LLM + `RouterSchema`; `_is_explicit_request()` override for "send me the report" style → force **respond**.                                   |
| `nodes/triage_interrupt.py`            | **triage_interrupt_handler:** On **notify**, calls `interrupt()`; user resumes with `Command(resume="respond")` or `"ignore"`.                                   |
| `nodes/prepare_messages.py`            | Injects reply context (and Gmail-inbox note) when `email_id`/`email_input` set; then goes to Response subgraph.                                                  |
| `nodes/mark_as_read.py`                | Marks Gmail message read when `email_id` is set (after response).                                                                                                |
| **tools/**                             |                                                                                                                                                                  |
| `tools/__init__.py`                    | `get_tools()` → send_email_tool, question_tool, done_tool.                                                                                                       |
| `tools/common.py`                      | question_tool, done_tool.                                                                                                                                        |
| `tools/gmail/auth.py`                  | Gmail OAuth: `get_credentials()`, `get_gmail_service()`.                                                                                                         |
| `tools/gmail/send_email.py`            | send_new_email, send_reply_email, send_email_tool (supports `email_id` for reply).                                                                               |
| `tools/gmail/mark_as_read.py`          | mark_as_read(email_id).                                                                                                                                          |
| `tools/gmail/fetch_emails.py`          | list_inbox_message_ids, get_message_as_email_input, fetch_recent_inbox; used by watcher.                                                                         |
| `tools/gmail/prompt_templates.py`      | get_gmail_tools_prompt(), GMAIL_TOOLS_PROMPT.                                                                                                                    |
| **db/**                                |                                                                                                                                                                  |
| `db/checkpointer.py`                   | **Sync** checkpointer: `postgres_checkpointer()` (search_path=email_assistant, prepare_threshold=None); `run_checkpoint_created_at_migration()`. Used by CLI.    |
| `db/studio_checkpointer.py`            | **Async** checkpointer: `generate_checkpointer()` for LangGraph Studio; same schema and Supabase-friendly options.                                               |
| `db/store.py`                          | PostgresStore in email_assistant schema; `setup_store()`, `postgres_store()`; prepare_threshold=None.                                                            |
| `db/persist_messages.py`               | Writes chats/messages to app tables after each run when DATABASE_URL set.                                                                                        |
| **fixtures/**                          |                                                                                                                                                                  |
| `fixtures/mock_emails.py`              | MOCK_EMAIL_NOTIFY, MOCK_EMAIL_RESPOND, MOCK_EMAIL_IGNORE; `get_mock_email(name)`.                                                                                |


---

## Scripts: `scripts/`


| Script                    | Purpose                                                                                                                                                                |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `run_agent.py`            | Run graph (question or email mode via env). On notify interrupt, prompts (r)espond/(i)gnore and resumes with Command(resume=...). Uses Postgres when DATABASE_URL set. |
| `run_mock_email.py`       | Run with a mock email (notify/respond/ignore). On notify, prompts and resumes. Uses Postgres when DATABASE_URL set.                                                    |
| `simulate_gmail_email.py` | Simulate Gmail-style flow with mock payload; prints triage and notify choice.                                                                                          |
| `watch_gmail.py`          | Poll Gmail INBOX, invoke graph per new message; stores processed ids in `.gmail_processed_ids.json`.                                                                   |
| `test_gmail_read.py`      | Test Gmail OAuth and read (list + get one message).                                                                                                                    |
| `setup_db.py`             | One-time: checkpointer.setup(), run 002 migration (created_at), store.setup().                                                                                         |
| `debug_triage.py`         | Debug triage: run input_router + triage_router locally; optional payload file.                                                                                         |


---

## Config and migrations


| File                                        | Purpose                                                                                                         |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `langgraph.json`                            | LangGraph Studio: graphs path, env file, checkpointer path (`db/studio_checkpointer.py:generate_checkpointer`). |
| `migrations/001_email_assistant_tables.sql` | App schema: users, chats, messages, agent_memory (email_assistant schema).                                      |
| `migrations/002_checkpoint_created_at.sql`  | Add created_at to checkpoint tables in email_assistant.                                                         |


---

## Other docs (in docs/)

- **ARCHITECTURE.md** — Flow and graph structure.
- **DATABASE.md** — Schema, checkpointer, store.
- **CONFIGURATION.md** — Env vars.
- **PROMPTS.md** — Prompt locations.
- **RUNNING_AND_TESTING.md** — Run and test instructions.
- **PROJECT_SUMMARY.md** — Phases and history.

---

*For architecture and flow, see **03_ARCHITECTURE_AND_FLOW.md**. For what has been implemented, see **09_WHAT_WE_HAVE_DONE.md**.*