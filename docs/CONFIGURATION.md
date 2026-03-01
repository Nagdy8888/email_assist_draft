# Configuration

Environment variables, `.env.example`, and security.

## Environment variables

All required and optional variables are documented in `.env.example`:

| Variable | Purpose |
|----------|--------|
| `OPENAI_API_KEY` | OpenAI API key for router and response LLMs |
| `OPENAI_MODEL` | Model name (e.g. `gpt-4o`) |
| `LANGCHAIN_TRACING_V2` | Enable LangSmith tracing (`true`/`false`) |
| `LANGCHAIN_API_KEY` | LangSmith API key |
| `LANGCHAIN_PROJECT` | LangSmith project name (e.g. `email-assistant`) |
| `GOOGLE_TOKEN_PATH` | Path to Gmail OAuth token (e.g. `.secrets/token.json`) |
| `GOOGLE_CREDENTIALS_PATH` | OAuth client secrets JSON from Google Cloud Console (e.g. `.secrets/credentials.json`). Required for first-time Gmail auth; browser flow saves token to `GOOGLE_TOKEN_PATH`. |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/service key |
| `DATABASE_URL` | Postgres connection string (checkpointer, store, and app tables). When set, run script uses Postgres and persists messages. |
| `USER_ID` | User identifier for persisted chats (default: `default-user`). Optional. |

**Optional for run script:** `RUN_MESSAGE` (default: "Hello, how are you?"), `THREAD_ID` (default: "default-thread"). For **email mode**: `RUN_EMAIL_FROM`, `RUN_EMAIL_TO`, `RUN_EMAIL_SUBJECT`, `RUN_EMAIL_BODY`, `RUN_EMAIL_ID` (optional) — see `docs/RUNNING_AND_TESTING.md`.

**Gmail watcher** (`scripts/watch_gmail.py`): `GMAIL_POLL_INTERVAL` (seconds between polls, default `60`), `GMAIL_UNREAD_ONLY` (`1` = only unread, default; `0` = recent inbox), `GMAIL_MAX_RESULTS` (max messages per poll, default `20`), `GMAIL_PROCESSED_IDS_FILE` (path to JSON file for processed message ids; default `.gmail_processed_ids.json` in project root). Optional: add that file to `.gitignore`.

**LangGraph Studio:** `langgraph dev` reads `langgraph.json` and loads `.env`. No extra env vars are required beyond `OPENAI_API_KEY` (and optional LangSmith vars).

Copy `.env.example` to `.env` and fill in values. **Do not commit `.env`**; it is listed in `.gitignore`.
