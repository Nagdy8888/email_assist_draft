# 05 — Database and persistence

Schema, checkpointer, store, and how to set them up.

---

## Schemas and tables

All application and LangGraph tables live in the **email_assistant** schema (not `public`).

### Application tables (you create once)

Defined in **`migrations/001_email_assistant_tables.sql`**. Run this SQL once (e.g. Supabase SQL editor or `psql`):

- **email_assistant.users** — Optional; one row per user.
- **email_assistant.chats** — One row per conversation; `chat_id` from LangGraph `thread_id`.
- **email_assistant.messages** — One message per row; written by `persist_messages()` after each run when `DATABASE_URL` is set.
- **email_assistant.agent_memory** — For Phase 6 memory/preferences; use `chat_id = NULL` for global prefs.

### LangGraph checkpointer tables (created by setup_db.py)

Created by **`checkpointer.setup()`** when you run **`scripts/setup_db.py`** once:

- **email_assistant.checkpoint_migrations** — Schema version for checkpointer.
- **email_assistant.checkpoints** — Graph state at each step.
- **email_assistant.checkpoint_blobs** — Larger checkpoint payloads.
- **email_assistant.checkpoint_writes** — Pending writes metadata.

**Migration 002** (`migrations/002_checkpoint_created_at.sql`) adds **created_at** to these tables; `setup_db.py` runs it after `cp.setup()`.

### LangGraph store tables (created by setup_db.py)

Created by **`store.setup()`** in the same `setup_db.py` run:

- **email_assistant.store** — Key/value store for memory (Phase 6).
- **email_assistant.store_migrations** — Schema version for store.

---

## Connections

- **CLI (run_agent.py, run_mock_email.py, watch_gmail.py):** Use **`db/checkpointer.py`** — sync Postgres connection with **`search_path = email_assistant`** and **`prepare_threshold=None`** (avoids DuplicatePreparedStatement with Supabase).
- **LangGraph Studio:** Uses **`db/studio_checkpointer.py`** — async context manager `generate_checkpointer()`; same schema and `prepare_threshold=None`. Referenced in **`langgraph.json`** as `checkpointer.path`.
- **Store:** **`db/store.py`** uses a dedicated connection with **`search_path = email_assistant`** and **`prepare_threshold=None`** for both `setup_store()` and `postgres_store()`.

---

## One-time setup

1. Run **`migrations/001_email_assistant_tables.sql`** on your Postgres.
2. Set **`DATABASE_URL`** in `.env` (e.g. Supabase connection string).
3. Run **`uv run python scripts/setup_db.py`** to create checkpointer and store tables (and run migration 002).

After that, CLI and Studio will persist checkpoints (and messages when persist_messages runs) in the **email_assistant** schema.

---

## Checkpoint tables empty?

- Query the **email_assistant** schema:  
  `SELECT * FROM email_assistant.checkpoints ORDER BY created_at DESC LIMIT 10;`
- Ensure **DATABASE_URL** is in `.env` and **restart** `langgraph dev` after changing it.
- Verify with CLI: e.g. `THREAD_ID=test-1 uv run python scripts/run_mock_email.py respond`, then  
  `SELECT * FROM email_assistant.checkpoints WHERE thread_id = 'test-1';`

See **../RUNNING_AND_TESTING.md** (section "Checkpoints in Supabase") for more troubleshooting.

---

## Related docs

- **06_CONFIGURATION.md** — DATABASE_URL and other env vars.
- **08_RUNNING_AND_TESTING.md** — setup_db.py and Studio checkpointer.
