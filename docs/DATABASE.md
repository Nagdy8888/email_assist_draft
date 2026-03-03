# Database

Schema, migrations, store, and checkpointer.

## Application tables (Supabase/Postgres)

Defined in `migrations/001_email_assistant_tables.sql`. Run this SQL once against your Postgres (e.g. Supabase SQL editor or `psql`).

- **email_assistant.users** — Optional; one row per user. Used to key chats and messages.
- **email_assistant.chats** — One row per conversation; `chat_id` is derived from LangGraph `thread_id` (stable UUID5).
- **email_assistant.messages** — One row per message (user/assistant/system/tool); queryable chat history. Written by `persist_messages()` after each run when `DATABASE_URL` is set.
- **email_assistant.agent_memory** — Backs the memory store for user preferences (Phase 6). For preferences use `chat_id = NULL`.

## LangGraph checkpointer

- **Connection:** Direct Postgres via `DATABASE_URL`. The project uses a connection with `search_path = email_assistant` so all checkpoint tables live in the **email_assistant** schema (same as app tables). See `db/checkpointer.py` (sync for CLI) and `db/studio_checkpointer.py` (async for LangGraph Studio).
- **Storage:** When `DATABASE_URL` is your **Supabase Postgres** connection string, checkpoint data is stored in Supabase. Run `scripts/setup_db.py` once to create the checkpoint tables in the `email_assistant` schema. **LangGraph Studio** uses the same Supabase checkpointer when `langgraph.json` has `"checkpointer": {"path": "...:generate_checkpointer"}` and `DATABASE_URL` is set.
- **Tables:** Created by `checkpointer.setup()` (run once via `scripts/setup_db.py`). Tables: `checkpoint_migrations`, `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`. Migration `migrations/002_checkpoint_created_at.sql` adds a `created_at TIMESTAMPTZ NOT NULL DEFAULT now()` column to each; `setup_db.py` runs it after `cp.setup()`. The `postgres_checkpointer()` context manager does not call `setup()` on each use, so you must run `setup_db.py` once; this also avoids `DuplicatePreparedStatement` when using pooled connections (e.g. Supabase).
- **Checkpoint tables empty?** Ensure you query the **email_assistant** schema: `SELECT * FROM email_assistant.checkpoints;` (not `public.checkpoints`). If using Studio, set `DATABASE_URL` in `.env` and **restart** `langgraph dev` so the server loads it and injects the checkpointer. To verify writes: run `THREAD_ID=test-1 uv run python scripts/run_mock_email.py respond`, then `SELECT * FROM email_assistant.checkpoints WHERE thread_id = 'test-1';`.

## LangGraph store (memory)

- **Connection:** Same `DATABASE_URL`. Use `postgres_store()` or raw `Connection` with `search_path = email_assistant` and `prepare_threshold=None` (see `db/store.py`) to avoid DuplicatePreparedStatement with Supabase/pooled connections.
- **Table:** Created by `store.setup()` (run once via `scripts/setup_db.py`). Table: `store` (and `store_migrations`) in the **email_assistant** schema. Used in Phase 6 for get_memory/update_memory.

## One-time setup

1. Run `migrations/001_email_assistant_tables.sql` against your Postgres.
2. Set `DATABASE_URL` in `.env`.
3. Run `python scripts/setup_db.py` (or `uv run python scripts/setup_db.py`) to create checkpoint and store tables.

After that, `run_agent.py` will use the Postgres checkpointer and persist messages when `DATABASE_URL` is set.
