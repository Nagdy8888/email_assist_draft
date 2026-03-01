# Project overview

**Email Assistant** is a LangGraph-based agent that:

- **Processes emails**: triage (ignore / notify / respond), with human-in-the-loop for notify.
- **Answers questions**: direct user questions (no triage) with optional tools (calendar, etc.).
- **Sends email**: reply to triaged email or send a new email to a specified address on request.

Tech stack: LangGraph, LangChain, OpenAI, Supabase, Postgres (checkpointer + optional store), Gmail API, optional Google Calendar.

## Current state (Phase 5)

- **Phase 1:** All dependencies and full project structure (stubs) in place.
- **Phase 2:** Simple agent: user message → LLM response; in-memory or Postgres checkpointer.
- **Phase 3:** Supabase/Postgres: app tables, checkpointer, store; messages persisted when `DATABASE_URL` is set.
- **Phase 4:** send_email_tool (new email + reply by email_id), question_tool, done_tool; Gmail OAuth; tool-call loop (chat → tools → persist).
- **Phase 5:** **Email mode** and **triage**. Input can be `email_input` (triage path) or `user_message` (question path). **input_router** → triage_router or response_agent. **triage_router** classifies ignore / notify / respond (LLM + RouterSchema). **notify** path uses **interrupt()**; user resumes with `Command(resume="respond")` or `Command(resume="ignore")`. **respond** path runs response_agent subgraph with email context and **mark_as_read** after. Reply via `send_email_tool(..., email_id=...)`; **mark_as_read** Gmail tool and node implemented.
- When an email is **passed in** as `email_input` (e.g. from run_agent.py, Studio, or a script that fetches Gmail), the agent sees it and runs classification and the full flow. For **automatic** ingestion of real Gmail inbox mail, run **`scripts/watch_gmail.py`**; it polls Gmail and invokes the graph for each new (unread) email.
- See **README.md** and **docs/RUNNING_AND_TESTING.md** for setup and Gmail OAuth.
