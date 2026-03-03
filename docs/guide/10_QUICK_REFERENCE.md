# 10 — Quick reference

Commands, inputs, and troubleshooting at a glance.

---

## Commands

| What | Command |
|------|--------|
| Run (question) | `uv run python scripts/run_agent.py` |
| Run (email) | Set RUN_EMAIL_* in .env, then `uv run python scripts/run_agent.py` |
| Mock email | `uv run python scripts/run_mock_email.py` or `uv run python scripts/run_mock_email.py respond` |
| Simulate Gmail | `uv run python scripts/simulate_gmail_email.py` |
| Gmail watcher | `uv run python scripts/watch_gmail.py` |
| Test Gmail read | `uv run python scripts/test_gmail_read.py` |
| Setup DB (once) | `uv run python scripts/setup_db.py` |
| Debug triage | `uv run python scripts/debug_triage.py` or `uv run python scripts/debug_triage.py payload.json` |
| LangGraph Studio | `uv run langgraph dev` |

---

## Run input (Studio / API)

| Mode | Example |
|------|--------|
| Question | `{"user_message": "Hello"}` |
| Email (triage) | `{"email_input": {"from": "...", "to": "...", "subject": "...", "body": "..."}}` |

Use **email_input** for triage; typing in the chat sends **user_message** (question path).

---

## Notify interrupt (HITL)

- **CLI:** When the graph pauses, type **r** (respond) or **i** (ignore) and press Enter.
- **Studio:** Use the resume control and send the value **"respond"** or **"ignore"**.

Requires a **checkpointer** (Postgres or MemorySaver) and same **thread_id** when resuming.

---

## Env (minimal)

- **OPENAI_API_KEY** — Required.
- **DATABASE_URL** — Postgres (Supabase) for checkpointer/store and message persistence; set and restart `langgraph dev` for Studio.
- **GOOGLE_CREDENTIALS_PATH** / **GOOGLE_TOKEN_PATH** — For Gmail (optional).

---

## Troubleshooting

| Issue | Check |
|-------|--------|
| Triage says ignore for "send me the report" | Run `uv run python scripts/debug_triage.py`; ensure run input uses **email_input** and not only chat. |
| Studio: empty email after input_router | Run input may be double-wrapped; input_router unwraps `{"email_input": {"email_input": {...}}}`. |
| Checkpoint tables empty | Query **email_assistant.checkpoints** (not public). Set DATABASE_URL and **restart** `langgraph dev`. Verify with CLI: THREAD_ID=test-1 + run_mock_email then SELECT by thread_id. |
| Gmail 403 / can't read | Delete or rename `.secrets/token.json`, run `uv run python scripts/test_gmail_read.py` to re-run OAuth with read scope. |
| Store setup fails (DuplicatePreparedStatement) | Fixed in store.py (prepare_threshold=None). Re-run `uv run python scripts/setup_db.py`. |

---

## Doc index (this set, in docs/guide/)

| # | File | Content |
|---|------|--------|
| 01 | 01_OVERVIEW.md | Project overview and tech stack |
| 02 | 02_PROJECT_STRUCTURE.md | Project structure and usage of each file |
| 03 | 03_ARCHITECTURE_AND_FLOW.md | Architecture and graph flow |
| 04 | 04_EMAIL_TRIAGE_AND_HITL.md | Email triage and human-in-the-loop |
| 05 | 05_DATABASE_AND_PERSISTENCE.md | Database, checkpointer, store |
| 06 | 06_CONFIGURATION.md | Configuration and env vars |
| 07 | 07_PROMPTS_AND_SCHEMAS.md | Prompts and schemas |
| 08 | 08_RUNNING_AND_TESTING.md | Running and testing |
| 09 | 09_WHAT_WE_HAVE_DONE.md | What we have done till now |
| 10 | 10_QUICK_REFERENCE.md | This quick reference |

For more detail, see the other files in **docs/** (e.g. RUNNING_AND_TESTING.md, DATABASE.md, CONFIGURATION.md).
