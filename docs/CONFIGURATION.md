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
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/service key |
| `DATABASE_URL` | Postgres connection string (checkpointer, store, and app tables). When set, run script uses Postgres and persists messages. |
| `USER_ID` | User identifier for persisted chats (default: `default-user`). Optional. |

**Optional for run script:** `RUN_MESSAGE` (default: "Hello, how are you?"), `THREAD_ID` (default: "default-thread") — see `docs/RUNNING_AND_TESTING.md`.

**LangGraph Studio:** `langgraph dev` reads `langgraph.json` and loads `.env`. No extra env vars are required beyond `OPENAI_API_KEY` (and optional LangSmith vars).

Copy `.env.example` to `.env` and fill in values. **Do not commit `.env`**; it is listed in `.gitignore`.
