# Project overview

**Email Assistant** is a LangGraph-based agent that:

- **Processes emails**: triage (ignore / notify / respond), with human-in-the-loop for notify.
- **Answers questions**: direct user questions (no triage) with optional tools (calendar, etc.).
- **Sends email**: reply to triaged email or send a new email to a specified address on request.

Tech stack: LangGraph, LangChain, OpenAI, Supabase, Postgres (checkpointer + optional store), Gmail API, optional Google Calendar.

## Current state (Phase 4)

- **Phase 1:** All dependencies and full project structure (stubs) in place.
- **Phase 2:** Simple agent: user message → LLM response; in-memory or Postgres checkpointer.
- **Phase 3:** Supabase/Postgres: app tables, checkpointer, store; messages persisted when `DATABASE_URL` is set.
- **Phase 4:** User can ask the agent to **send an email** to a specific address. Implemented: **send_email_tool** (new email only), **question_tool**, **done_tool**; Gmail OAuth via `.secrets/credentials.json` and `.secrets/token.json`; tool-call loop (chat → tools → chat → persist). Messages still stored in Supabase. Reply by `email_id` is Phase 5.
- See **README.md** and **docs/RUNNING_AND_TESTING.md** for setup and Gmail OAuth.
