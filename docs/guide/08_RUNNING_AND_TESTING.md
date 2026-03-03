# 08 — Running and testing

How to run the agent and test triage, HITL, and Studio.

---

## Quick start

1. Copy `.env.example` to `.env` and set **OPENAI_API_KEY** (and optionally **DATABASE_URL**).
2. **Question mode:**  
   `uv run python scripts/run_agent.py`  
   (default message or set **RUN_MESSAGE** in `.env`.)
3. **Email mode:** Set **RUN_EMAIL_FROM**, **RUN_EMAIL_TO**, **RUN_EMAIL_SUBJECT**, **RUN_EMAIL_BODY** (and optionally **RUN_EMAIL_ID**), then run the same script.

When classification is **notify**, the script prompts "Resume with (r)espond or (i)gnore?" and resumes with `Command(resume=...)` until the run completes.

---

## Mock email (no Gmail API)

- **Default (notify):**  
  `uv run python scripts/run_mock_email.py`  
  On notify interrupt, script prompts (r)espond or (i)gnore and resumes.
- **Specific fixture:**  
  `MOCK_EMAIL=respond uv run python scripts/run_mock_email.py`  
  or  
  `uv run python scripts/run_mock_email.py ignore`

When **DATABASE_URL** is set, the run uses the Postgres checkpointer (email_assistant schema).

---

## LangGraph Studio

1. From project root:  
   `uv run langgraph dev`
2. Open the Studio URL (e.g. `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`).
3. **Question mode:** Run input `{"user_message": "Hello"}`.
4. **Email mode (triage):** Run input must include **email_input**, e.g.  
   `{"email_input": {"from": "...", "to": "...", "subject": "...", "body": "..."}}`  
   (If you paste a double-wrapped payload like `{"email_input": {"email_input": {...}}}`, the input_router unwraps it.)
5. When the run **pauses** (notify), use Studio's resume control and send **"respond"** or **"ignore"**.

Set **DATABASE_URL** in `.env` and **restart** `langgraph dev` so Studio uses the Supabase checkpointer. Checkpoints are stored in the **email_assistant** schema.

---

## Gmail watcher (automatic inbox)

- **Terminal 1:** `uv run langgraph dev` (for Studio).
- **Terminal 2:** `uv run python scripts/watch_gmail.py`

Requires Gmail OAuth (`.secrets/credentials.json`, `.secrets/token.json`). Test read access first: **`uv run python scripts/test_gmail_read.py`**. If you get 403, delete or rename `.secrets/token.json` and run the test again to re-run OAuth with read scope.

---

## Debug triage

If an email that should be **respond** is classified as **ignore** (e.g. in Studio):

1. Run:  
   `uv run python scripts/debug_triage.py`  
   Uses MOCK_EMAIL_RESPOND, runs input_router + triage_router, prints whether the override fired and the final classification.
2. To test the exact Studio payload, save the run input JSON to a file (e.g. `payload.json`) and run:  
   `uv run python scripts/debug_triage.py payload.json`

---

## Database setup (one-time)

1. Run **`migrations/001_email_assistant_tables.sql`** on your Postgres.
2. Set **DATABASE_URL** in `.env`.
3. Run **`uv run python scripts/setup_db.py`** to create checkpointer and store tables (and migration 002).

See **05_DATABASE_AND_PERSISTENCE.md** and **../RUNNING_AND_TESTING.md** for more detail and troubleshooting (e.g. checkpoint tables empty, Studio resume, Gmail 403).
