# Project overview

**Email Assistant** is a LangGraph-based agent that:

- **Processes emails**: triage (ignore / notify / respond), with human-in-the-loop for notify.
- **Answers questions**: direct user questions (no triage) with optional tools (calendar, etc.).
- **Sends email**: reply to triaged email or send a new email to a specified address on request.

Tech stack: LangGraph, LangChain, OpenAI, Supabase, Postgres (checkpointer + optional store), Gmail API, optional Google Calendar.

## Current state (Phase 3)

- **Phase 1:** All dependencies and full project structure (stubs) in place.
- **Phase 2:** Simple agent: user message → LLM response; in-memory or Postgres checkpointer.
- **Phase 3:** Supabase/Postgres: app tables (users, chats, messages, agent_memory) via `migrations/001_email_assistant_tables.sql`. Postgres checkpointer and PostgresStore (setup via `scripts/setup_db.py`). When `DATABASE_URL` is set, the run script uses Postgres and **persists messages** to `email_assistant.messages` after each run. Agent behavior unchanged (question → response).
- See **README.md** for setup and **docs/RUNNING_AND_TESTING.md** and **docs/DATABASE.md** for running and DB setup.
