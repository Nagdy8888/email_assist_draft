# 01 — Project overview

High-level description of the Email Assistant project: what it is, what it does, and the tech stack.

---

## What is the Email Assistant?

**Email Assistant** is a LangGraph-based agent that:

1. **Processes incoming emails** — Classifies each email as **ignore**, **notify**, or **respond**. For **notify**, the graph pauses and asks you whether to respond or ignore (human-in-the-loop). For **respond**, it runs the response flow and can send a reply.
2. **Answers questions** — Handles direct user messages (question mode) with optional tools (send email, question, done).
3. **Sends email** — Can send a new email or reply to a triaged email using Gmail (OAuth).

Input can be an **email payload** (`email_input`) for triage, or a **user message** for simple Q&A. The agent uses a single top-level graph with two subagents: **Email Assistant** (triage + notify HITL) and **Response** (chat, tools, persist).

---

## Tech stack

| Layer        | Technology |
|-------------|------------|
| Agent / graph | LangGraph, LangChain |
| LLM         | OpenAI (e.g. `gpt-4o`) |
| Database    | Postgres / Supabase (`email_assistant` schema): checkpointer, store, app tables |
| Email       | Gmail API (OAuth); optional Google Calendar |
| Tracing     | Optional LangSmith |

---

## Current state

- **Phases 1–5** are done: project structure, simple agent, Postgres/Supabase (checkpointer, store, app tables), send-email tools, and **email mode + triage** with HITL on notify.
- **Phase 6** (memory/preferences) is partially in place.
- **Phase 7** (run script, notebook, docs) is done.

You can run the agent via CLI (`run_agent.py`, `run_mock_email.py`), LangGraph Studio (`langgraph dev`), or the Gmail watcher (`watch_gmail.py`) for automatic inbox ingestion.

---

## Related docs

- **02_PROJECT_STRUCTURE.md** — Project layout and usage of each file.
- **09_WHAT_WE_HAVE_DONE.md** — Phases and features implemented so far.
