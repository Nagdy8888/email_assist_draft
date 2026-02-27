# Database

Schema, migrations, store, and checkpointer.

## Application tables (Supabase/Postgres)

Defined in `migrations/001_email_assistant_tables.sql`. Run this SQL once against your Postgres (e.g. Supabase SQL editor or `psql`).

- **email_assistant.users** — Optional; one row per user. Used to key chats and messages.
- **email_assistant.chats** — One row per conversation; `chat_id` is derived from LangGraph `thread_id` (stable UUID5).
- **email_assistant.messages** — One row per message (user/assistant/system/tool); queryable chat history. Written by `persist_messages()` after each run when `DATABASE_URL` is set.
- **email_assistant.agent_memory** — Backs the memory store for user preferences (Phase 6). For preferences use `chat_id = NULL`.

## LangGraph checkpointer

- **Connection:** Direct Postgres via `DATABASE_URL` (not Supabase client). Use `PostgresSaver.from_conn_string(DATABASE_URL)` in `db/checkpointer.py`.
- **Tables:** Created by `checkpointer.setup()` (run once via `scripts/setup_db.py`). Tables live in the default schema: `checkpoint_migrations`, `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`.

## LangGraph store (memory)

- **Connection:** Same `DATABASE_URL`. Use `PostgresStore.from_conn_string(DATABASE_URL)` in `db/store.py`.
- **Table:** Created by `store.setup()` (run once via `scripts/setup_db.py`). Table: `store` (prefix, key, value, etc.). Used in Phase 6 for get_memory/update_memory.

## One-time setup

1. Run `migrations/001_email_assistant_tables.sql` against your Postgres.
2. Set `DATABASE_URL` in `.env`.
3. Run `python scripts/setup_db.py` (or `uv run python scripts/setup_db.py`) to create checkpoint and store tables.

After that, `run_agent.py` will use the Postgres checkpointer and persist messages when `DATABASE_URL` is set.
