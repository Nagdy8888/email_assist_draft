# 06 — Configuration

Environment variables and where they are used.

---

## Required

| Variable | Purpose |
|----------|--------|
| **OPENAI_API_KEY** | OpenAI API key for triage and response LLMs. |
| **OPENAI_MODEL** | Model name (default `gpt-4o`). |

---

## Database and Studio

| Variable | Purpose |
|----------|--------|
| **DATABASE_URL** | Postgres connection string (checkpointer, store, app tables). When set, CLI scripts use Postgres and can persist messages. For **LangGraph Studio** and mock-email testing, set to your **Supabase Postgres** connection string (Project Settings → Database → Connection string) and run **`uv run python scripts/setup_db.py`** once. Studio uses it when `langgraph.json` has `checkpointer.path` set. |
| **USER_ID** | User identifier for persisted chats (default `default-user`). Optional. |

---

## Gmail (optional)

| Variable | Purpose |
|----------|--------|
| **GOOGLE_CREDENTIALS_PATH** | OAuth client secrets JSON (e.g. `.secrets/credentials.json`). Required for first-time Gmail auth. |
| **GOOGLE_TOKEN_PATH** | Path to saved OAuth token (e.g. `.secrets/token.json`). Browser flow writes here after first auth. |

---

## Run script (optional)

| Variable | Purpose |
|----------|--------|
| **RUN_MESSAGE** | Default user message in question mode (default `"Hello, how are you?"`). |
| **THREAD_ID** | Thread id for checkpointing (default `default-thread`). |
| **RUN_EMAIL_FROM**, **RUN_EMAIL_TO**, **RUN_EMAIL_SUBJECT**, **RUN_EMAIL_BODY** | Email mode input when running via env. **RUN_EMAIL_ID** optional (Gmail message id). |

---

## Gmail watcher

| Variable | Purpose |
|----------|--------|
| **GMAIL_POLL_INTERVAL** | Seconds between polls (default `60`). |
| **GMAIL_UNREAD_ONLY** | `1` = only unread (default); `0` = recent inbox. |
| **GMAIL_MAX_RESULTS** | Max messages per poll (default `20`). |
| **GMAIL_PROCESSED_IDS_FILE** | Path to JSON file for processed message ids (default `.gmail_processed_ids.json`). |

---

## Mock and simulation scripts

| Variable | Purpose |
|----------|--------|
| **MOCK_EMAIL** | Fixture name for `run_mock_email.py`: `notify`, `respond`, or `ignore` (default `notify`). |
| **SIMULATE_EMAIL** | Fixture for `simulate_gmail_email.py`: `notify`, `respond`, or `ignore`. |

---

## LangSmith (optional)

| Variable | Purpose |
|----------|--------|
| **LANGCHAIN_TRACING_V2** | Set to `true` to enable tracing. |
| **LANGCHAIN_API_KEY** | LangSmith API key. |
| **LANGCHAIN_PROJECT** | LangSmith project name (e.g. `email-assistant`). |

---

## Setup

- Copy **`.env.example`** to **`.env`** and fill in values. Do not commit `.env` (it is in `.gitignore`).
- **LangGraph Studio:** `langgraph dev` loads `.env` from the project root. Restart the server after changing `.env` so it picks up `DATABASE_URL` and uses the Postgres checkpointer.

For the full list and script-specific notes, see **../CONFIGURATION.md**.
