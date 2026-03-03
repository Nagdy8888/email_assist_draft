# Explanation: Migrations (`migrations/`)

Detailed walkthrough of the **SQL migrations** in `migrations/`: they create or drop the **email_assistant** schema and define application tables (users, chats, messages, agent_memory) and add **created_at** to LangGraph checkpoint tables. Each file and statement is explained below.

---

## 1. Overview

| File | Purpose |
|------|--------|
| **000_drop_email_assistant_schema.sql** | Drop **email_assistant** schema and all objects (clean slate). Run first when you want to recreate everything. |
| **001_email_assistant_tables.sql** | Create **email_assistant** schema and app tables: **users**, **chats**, **messages**, **agent_memory**. Run after 000 for fresh install, or once when schema doesn’t exist. |
| **002_checkpoint_created_at.sql** | Add **created_at** to LangGraph checkpoint tables. Run **after** `scripts/setup_db.py` has created those tables (e.g. via `run_checkpoint_created_at_migration()`). |

**Note:** LangGraph checkpoint tables (e.g. **checkpoints**, **checkpoint_writes**, **checkpoint_blobs**, **checkpoint_migrations**) are **not** created by these migrations; they are created by **PostgresSaver.setup()** (in `scripts/setup_db.py` or Studio’s **generate_checkpointer**). Migrations 000 and 001 are for the **application** schema and tables; 002 only alters the existing checkpoint tables.

---

## 2. `000_drop_email_assistant_schema.sql`

**Purpose:** Remove the **email_assistant** schema and every object in it (tables, indexes, etc.). Use when you want a clean slate before re-running 001. **Destructive:** all data in the schema is deleted.

```sql
-- Drop the email_assistant schema and all objects in it.
-- Run this first when you want a clean slate, then run 001_email_assistant_tables.sql.
-- WARNING: This deletes all data in the schema.

DROP SCHEMA IF EXISTS email_assistant CASCADE;
```

- **DROP SCHEMA IF EXISTS email_assistant CASCADE:** Drops the schema if it exists. **CASCADE** drops all objects in the schema (tables, views, functions, etc.) and their dependencies. Safe to run when the schema doesn’t exist (**IF EXISTS**). After this, 001 can create the schema and tables from scratch.
- **When to run:** Only when you intend to wipe and recreate **email_assistant** (e.g. local dev reset). Do **not** run in production unless you mean to delete all data in that schema.

---

## 3. `001_email_assistant_tables.sql`

**Purpose:** Create the **email_assistant** schema and the application tables used by **persist_messages**, optional store, and future features: **users**, **chats**, **messages**, **agent_memory**. LangGraph checkpoint tables are created separately by **checkpointer.setup()**.

### Schema

```sql
CREATE SCHEMA email_assistant;
```

- Creates the **email_assistant** schema. All application tables and (when **search_path** is set) the LangGraph checkpoint tables live in this schema so they’re grouped and avoid name clashes with other schemas.

### Table: `email_assistant.users`

```sql
CREATE TABLE email_assistant.users (
  user_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email           TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- **user_id:** Primary key. **persist_messages** uses a UUID derived from **user_id** (or from config) and upserts into **users** so each run has a user row. **chats** and **messages** reference **user_id**.
- **email:** Optional; for future use (e.g. link to Gmail identity).
- **created_at / updated_at:** Timestamps; **persist_messages** does **ON CONFLICT (user_id) DO UPDATE SET updated_at = now()**.

### Table: `email_assistant.chats`

```sql
CREATE TABLE email_assistant.chats (
  chat_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES email_assistant.users(user_id) ON DELETE CASCADE,
  title           TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_chats_user_id ON email_assistant.chats(user_id);
```

- **chat_id:** Primary key. **persist_messages** derives **chat_id** from **thread_id** via **thread_id_to_chat_id()** (UUID5) and upserts into **chats** so one chat row per thread.
- **user_id:** FK to **users**; **ON DELETE CASCADE** so deleting a user deletes their chats.
- **title:** Optional; for UI or display.
- **created_at / updated_at:** Timestamps.
- **idx_chats_user_id:** Speeds up “list chats for user” queries.

### Table: `email_assistant.messages`

```sql
CREATE TABLE email_assistant.messages (
  message_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chat_id         UUID NOT NULL REFERENCES email_assistant.chats(chat_id) ON DELETE CASCADE,
  user_id         UUID NOT NULL REFERENCES email_assistant.users(user_id) ON DELETE CASCADE,
  role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
  content         TEXT,
  metadata        JSONB DEFAULT '{}',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_messages_chat_id ON email_assistant.messages(chat_id);
CREATE INDEX idx_messages_user_id ON email_assistant.messages(user_id);
CREATE INDEX idx_messages_created_at ON email_assistant.messages(chat_id, created_at);

ALTER TABLE email_assistant.messages ADD COLUMN email_id TEXT;
```

- **message_id:** Primary key; one row per message.
- **chat_id / user_id:** FKs to **chats** and **users**; **persist_messages** inserts rows with **chat_id** and **user_id** from the run.
- **role:** Matches **persist_messages** output: **user**, **assistant**, **system**, **tool** (from **_message_role**).
- **content:** Message text (or NULL); from **_message_content**.
- **metadata:** JSONB for **additional_kwargs** or other metadata; default **'{}'**.
- **created_at:** When the row was inserted.
- **email_id:** Added by **ALTER TABLE**; optional Gmail message id (e.g. for “reply to” context). Not required by **persist_messages** core flow but available for extensions.
- Indexes: by **chat_id** (list messages of a chat), **user_id** (messages by user), and **(chat_id, created_at)** for ordered history.

### Table: `email_assistant.agent_memory`

```sql
CREATE TABLE email_assistant.agent_memory (
  id              BIGSERIAL PRIMARY KEY,
  user_id         UUID NOT NULL REFERENCES email_assistant.users(user_id) ON DELETE CASCADE,
  chat_id         UUID REFERENCES email_assistant.chats(chat_id) ON DELETE CASCADE,
  namespace       TEXT NOT NULL,
  key             TEXT NOT NULL DEFAULT 'user_preferences',
  value           TEXT,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, chat_id, namespace, key)
);
CREATE INDEX idx_agent_memory_user_chat ON email_assistant.agent_memory(user_id, chat_id);
CREATE INDEX idx_agent_memory_namespace ON email_assistant.agent_memory(user_id, namespace);
```

- **agent_memory:** Key-value–style memory per (user, chat, namespace, key). Used for Phase 6 memory (e.g. user preferences, get_memory/update_memory) or future features. **LangGraph PostgresStore** may use a different table; this one is for application-level memory.
- **user_id / chat_id:** Scope memory to a user and optionally a chat; **chat_id** nullable for user-level memory.
- **namespace / key:** Logical grouping (e.g. namespace `"preferences"`, key `"response_style"`). **UNIQUE (user_id, chat_id, namespace, key)** allows one value per combination.
- **value:** Stored as TEXT; app can store JSON strings.
- **updated_at:** Last update time.
- Indexes: by **(user_id, chat_id)** and **(user_id, namespace)** for lookups.

---

## 4. `002_checkpoint_created_at.sql`

**Purpose:** Add a **created_at** column to the LangGraph checkpoint tables. Those tables are created by **PostgresSaver.setup()** (in **email_assistant** schema when **search_path** is set). Run this **after** `scripts/setup_db.py` has called **cp.setup()**, or from **run_checkpoint_created_at_migration()** in **db/checkpointer.py**. Idempotent: **ADD COLUMN IF NOT EXISTS**.

```sql
-- Add created_at timestamp to LangGraph checkpoint tables (in email_assistant schema).
-- Run AFTER scripts/setup_db.py has created the checkpoint tables (cp.setup()).
-- Idempotent: ADD COLUMN IF NOT EXISTS.

ALTER TABLE checkpoint_migrations ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE checkpoints           ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE checkpoint_blobs      ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE checkpoint_writes     ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
```

- **checkpoint_migrations, checkpoints, checkpoint_blobs, checkpoint_writes:** Tables created by LangGraph’s **PostgresSaver.setup()**. They live in **email_assistant** when the connection uses **SET search_path TO email_assistant** (as in **postgres_checkpointer()** and **run_checkpoint_created_at_migration()**). So these **ALTER**s apply to **email_assistant.checkpoint_***.
- **created_at:** Timestamp for when each row was created; useful for auditing and cleanup. **NOT NULL DEFAULT now()** so existing rows get a value.
- **IF NOT EXISTS:** Safe to run multiple times; no error if the column already exists.

---

## 5. Run order

1. **Fresh install (reset):** Run **000** (drop schema), then **001** (create schema and app tables). Then run **scripts/setup_db.py** to create LangGraph checkpoint and store tables. Then run **002** (or let **setup_db.py** call **run_checkpoint_created_at_migration()**).
2. **First install (no schema yet):** Run **001** only (skip 000). Then **scripts/setup_db.py**, then **002** (or via setup_db).
3. **002 only:** If checkpoint tables already exist (e.g. from a previous setup_db) and you just need **created_at**, run **002** with **search_path=email_assistant** (as in **run_checkpoint_created_at_migration()**).

---

## 6. Related files

- **persist_messages:** `src/email_assistant/db/persist_messages.py` (writes to **users**, **chats**, **messages**).
- **Checkpointer:** `src/email_assistant/db/checkpointer.py` (PostgresSaver creates checkpoint tables; **run_checkpoint_created_at_migration()** runs 002).
- **Setup script:** `scripts/setup_db.py` (creates checkpoint tables and store; calls **run_checkpoint_created_at_migration()**).
- **Store:** `src/email_assistant/db/store.py` (PostgresStore table; separate from 001).

For config (DATABASE_URL and schema usage), see **docs/code-explanations/config.md**. For checkpointer and persist_messages, see **docs/code-explanations/db_checkpointer.md** and **docs/code-explanations/db_persist_messages.md**.
