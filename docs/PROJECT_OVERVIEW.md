# Project overview

**Email Assistant** is a LangGraph-based agent that:

- **Processes emails**: triage (ignore / notify / respond), with human-in-the-loop for notify.
- **Answers questions**: direct user questions (no triage) with optional tools (calendar, etc.).
- **Sends email**: reply to triaged email or send a new email to a specified address on request.

Tech stack: LangGraph, LangChain, OpenAI, Supabase, Postgres (checkpointer + optional store), Gmail API, optional Google Calendar.

## Current state (Phase 6/7)

- **Phase 1:** All dependencies and full project structure; **utils.py** (parse_gmail, format_gmail_markdown, format_for_display).
- **Phase 2:** Simple agent: user message → LLM response; in-memory or Postgres checkpointer.
- **Phase 3:** Supabase/Postgres: app tables, checkpointer, store; messages persisted when `DATABASE_URL` is set.
- **Phase 4/5:** send_email_tool (new + reply), fetch_emails_tool, check_calendar_tool, schedule_meeting_tool, question_tool, done_tool; Gmail + Calendar OAuth; **email mode** and **triage** (ignore/notify/respond); **notify** HITL (interrupt → respond/ignore); **mark_as_read**.
- **Phase 6:** **Memory**: get_memory/update_memory in **memory.py**; preferences (triage_preferences, response_preferences, cal_preferences) loaded from store and injected into triage and response prompts when graph is compiled with **store**. **Tool-approval HITL**: before send_email_tool or schedule_meeting_tool, **tool_approval_gate** calls interrupt(); resume with `Command(resume=True)` or `False`. run_agent.py uses Postgres store when `DATABASE_URL` is set.
- **Phase 7:** **notebooks/run_agent_sdk.ipynb** runs the agent (question mode, email mode, HITL resume). **docs/GLOSSARY.md** for key terms.
- When an email is **passed in** as `email_input` (e.g. from run_agent.py, Studio, or a script that fetches Gmail), the agent runs triage and the full flow. For **automatic** ingestion, run **`scripts/watch_gmail.py`**.
- See **README.md** and **docs/RUNNING_AND_TESTING.md** for setup and Gmail OAuth. **docs/guide/DOCS_INDEX.md** for the 10-file guide.
