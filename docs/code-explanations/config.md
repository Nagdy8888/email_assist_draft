# Explanation: Config (`.env.example` and `langgraph.json`)

Detailed walkthrough of **configuration**: environment variables (`.env.example`) and the LangGraph dev server config (`langgraph.json`). Each item is explained below.

---

## 1. Overview

| Source | Purpose |
|--------|--------|
| **.env.example** | Template for environment variables: OpenAI, LangSmith, Gmail OAuth, Supabase, Postgres, USER_ID. Copy to `.env` and fill values. |
| **langgraph.json** | Config for `langgraph dev`: which graph to serve, which checkpointer to inject, and env file path. |

---

## 2. `.env.example`

**Purpose:** List all environment variables the project uses so you can copy the file to `.env` and set values. The app and scripts read these via `os.getenv(...)` or `load_dotenv()` then `os.getenv(...)`.

### Snippets (by section)

```bash
# OpenAI
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o
```

- **OPENAI_API_KEY:** Required for LLM calls (triage, response agent). Used in `prompts`/nodes and `simple_agent` (ChatOpenAI). Leave empty in `.env.example`; set in real `.env` (never commit `.env`).
- **OPENAI_MODEL:** Model name for ChatOpenAI (e.g. `gpt-4o`). Default in code is often `gpt-4o`; override here for a different model.

```bash
# LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=email-assistant
```

- **LANGCHAIN_TRACING_V2:** When `true`, LangChain/LangSmith tracing is enabled (if **LANGCHAIN_API_KEY** is set). Used by the LangChain runtime for observability.
- **LANGCHAIN_API_KEY:** LangSmith API key for sending traces. Optional; leave empty to disable.
- **LANGCHAIN_PROJECT:** Project name in LangSmith for grouping runs. Optional.

```bash
# Google / Gmail
GOOGLE_TOKEN_PATH=.secrets/token.json
GOOGLE_CREDENTIALS_PATH=.secrets/credentials.json
```

- **GOOGLE_TOKEN_PATH:** Path to the OAuth token file (created after first browser login). Relative path is resolved against project root in `tools/gmail/auth.py` (`_resolve_path`). Default `.secrets/token.json`.
- **GOOGLE_CREDENTIALS_PATH:** Path to the OAuth client secrets JSON from Google Cloud Console. Used by `auth.get_credentials()` when running the OAuth flow. Default `.secrets/credentials.json`. Gmail tools (send_email, mark_as_read, fetch_emails) and scripts (watch_gmail, test_gmail_read) need valid token (and credentials for first run).

```bash
# Supabase
SUPABASE_URL=
SUPABASE_KEY=
```

- **SUPABASE_URL / SUPABASE_KEY:** Supabase project URL and key. Documented here for apps that use Supabase client directly; the current codebase uses **DATABASE_URL** (Postgres connection string) for checkpointer, store, and persist_messages. Supabase Postgres connection string is typically used as **DATABASE_URL**.

```bash
# Postgres (checkpointer + optional store)
DATABASE_URL=
```

- **DATABASE_URL:** Postgres connection string (e.g. Supabase “Connection string” or any Postgres URI). Used by:
  - **db/checkpointer.py** — `postgres_checkpointer()`, `run_checkpoint_created_at_migration()`
  - **db/studio_checkpointer.py** — `generate_checkpointer()` (LangGraph Studio)
  - **db/store.py** — `postgres_store()`, `setup_store()`
  - **db/persist_messages.py** — `persist_messages(conn_string, ...)` (called from `simple_agent._persist_messages_node`)
  - **scripts/setup_db.py** — requires it to create checkpoint and store tables
  - **scripts/run_agent.py**, **run_mock_email.py**, **watch_gmail.py** — use Postgres checkpointer when set

```bash
# Phase 3: user id for persisted chats (optional; default: default-user)
USER_ID=
```

- **USER_ID:** User identifier for persisted chats and checkpointer config. Scripts pass it in `config["configurable"]["user_id"]`; **get_config()** in `_persist_messages_node` and **persist_messages** use it for **email_assistant.users** and **messages.user_id**. Optional; default in scripts is often `"default-user"`.

### Script-only / run-time variables (not in .env.example)

These are often used by scripts via `os.getenv()` with defaults; they can be set in `.env` or the shell:

- **THREAD_ID** — e.g. `run_agent.py`, `run_mock_email.py` (defaults like `"default-thread"`, `"mock-hitl-1"`).
- **RUN_MESSAGE** — `run_agent.py` question-mode message (default `"Hello, how are you?"`).
- **RUN_EMAIL_FROM**, **RUN_EMAIL_TO**, **RUN_EMAIL_SUBJECT**, **RUN_EMAIL_BODY**, **RUN_EMAIL_ID** — `run_agent.py` email mode.
- **MOCK_EMAIL** — `run_mock_email.py` fixture name: `notify` | `respond` | `ignore`.
- **GMAIL_POLL_INTERVAL**, **GMAIL_UNREAD_ONLY**, **GMAIL_MAX_RESULTS**, **GMAIL_PROCESSED_IDS_FILE** — `watch_gmail.py`.
- **SIMULATE_EMAIL** — `simulate_gmail_email.py` fixture name.

---

## 3. `langgraph.json`

**Purpose:** Configuration for the **LangGraph dev server** (`langgraph dev`). It tells the server which graph to load, which checkpointer to use, and which env file to load. The server uses this when you develop or run the graph in LangGraph Studio.

### Snippets

```json
{
  "dependencies": ["."],
  "graphs": {
    "email_assistant": "./src/email_assistant/email_assistant_hitl_memory_gmail.py:email_assistant"
  },
  "env": ".env",
  "checkpointer": {
    "path": "./src/email_assistant/db/studio_checkpointer.py:generate_checkpointer"
  }
}
```

- **dependencies:** List of dependency paths for the server. **["."]** means the current directory (project root) is the dependency context so the server can resolve imports like `email_assistant.*`.

- **graphs:** Map of graph names to “module:attribute” paths. **"email_assistant"** is the graph name exposed in Studio. The value **"./src/email_assistant/email_assistant_hitl_memory_gmail.py:email_assistant"** means: load the module from that file and use the **email_assistant** attribute (the compiled graph from `email_assistant = build_email_assistant_graph()`). The server imports that symbol and serves it; the graph is built **without** a checkpointer in code, so the server must inject one.

- **env:** Path to the env file the server loads (e.g. before starting). **".env"** loads variables from the project root `.env` so **DATABASE_URL**, **OPENAI_API_KEY**, etc. are available when the server runs and when **generate_checkpointer** is invoked.

- **checkpointer.path:** Tells the server which checkpointer to use for the graph. **"./src/email_assistant/db/studio_checkpointer.py:generate_checkpointer"** means: load the **generate_checkpointer** async context manager from that module. The server enters it (e.g. at startup or per run) and passes the yielded **AsyncPostgresSaver** into the graph so Studio has persistent threads and HITL resume. **DATABASE_URL** must be set so **generate_checkpointer** can connect to Postgres.

---

## 4. Flow summary

1. **Local/CLI:** Copy `.env.example` to `.env`, set at least **OPENAI_API_KEY** and optionally **DATABASE_URL**, **GOOGLE_***, etc. Scripts call **load_dotenv()** then **os.getenv(...)**. When **DATABASE_URL** is set, checkpoint/store and persist_messages use Postgres; run **scripts/setup_db.py** once and ensure **migrations/001_email_assistant_tables.sql** has been run.
2. **LangGraph Studio:** Run `langgraph dev` from the project root. The server reads **langgraph.json**: loads the **email_assistant** graph from the given file and injects the checkpointer from **generate_checkpointer**. It loads **.env** so **DATABASE_URL** and **OPENAI_API_KEY** are available. Studio then serves the graph with persistence and HITL support.

---

## 5. Related files

- **Auth (Gmail):** `src/email_assistant/tools/gmail/auth.py` (GOOGLE_TOKEN_PATH, GOOGLE_CREDENTIALS_PATH, get_credentials).
- **Checkpointer:** `src/email_assistant/db/checkpointer.py` (DATABASE_URL, postgres_checkpointer), `src/email_assistant/db/studio_checkpointer.py` (generate_checkpointer, used by langgraph.json).
- **Store / persist:** `src/email_assistant/db/store.py`, `src/email_assistant/db/persist_messages.py` (DATABASE_URL).
- **LLM:** `src/email_assistant/simple_agent.py`, `src/email_assistant/nodes/triage.py` (OPENAI_API_KEY, OPENAI_MODEL).
- **Scripts:** All scripts in `scripts/` that use **load_dotenv()** and **os.getenv()`.

For checkpointer and Studio, see **docs/code-explanations/db_checkpointer.md** and **docs/code-explanations/db_studio_checkpointer.md**. For migrations (tables that use DATABASE_URL), see **docs/code-explanations/migrations.md**.
