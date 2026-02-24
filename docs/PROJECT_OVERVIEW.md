# Project overview

**Email Assistant** is a LangGraph-based agent that:

- **Processes emails**: triage (ignore / notify / respond), with human-in-the-loop for notify.
- **Answers questions**: direct user questions (no triage) with optional tools (calendar, etc.).
- **Sends email**: reply to triaged email or send a new email to a specified address on request.

Tech stack: LangGraph, LangChain, OpenAI, Supabase, Postgres (checkpointer + optional store), Gmail API, optional Google Calendar.

## Current state (Phase 2)

- **Phase 1:** All dependencies and full project structure (stubs) in place.
- **Phase 2:** Simple agent runs: user message → LLM response. One node, `MessagesState`, in-memory checkpointer (`MemorySaver`). Run with `python scripts/run_agent.py` (set `OPENAI_API_KEY` in `.env`). Multi-turn works with the same `thread_id`. No DB, no store, no email.
- See **README.md** for setup and **docs/RUNNING_AND_TESTING.md** for how to run and test.
