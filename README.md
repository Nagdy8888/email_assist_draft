# Email Assistant

LangGraph-based email assistant with triage, human-in-the-loop, memory, and Gmail integration.

## How to run

1. **Create virtual environment and install dependencies** (using [uv](https://docs.astral.sh/uv/)):

   ```bash
   uv venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # Unix
   uv sync
   ```

2. Copy `.env.example` to `.env` and set your API keys and configuration.

3. **(Optional) Phase 3 — Postgres:** Run `migrations/001_email_assistant_tables.sql` in your Postgres, set `DATABASE_URL` in `.env`, then run `uv run python scripts/setup_db.py` once. After that, the run script will persist messages to the DB.

4. Run the simple agent:

   ```bash
   python scripts/run_agent.py
   ```
   Set `OPENAI_API_KEY` in `.env`. Optionally set `RUN_MESSAGE`, `THREAD_ID`, and (Phase 3) `USER_ID`.

5. **(Optional) Phase 4 — send email:** To let the agent send emails via Gmail, add `.secrets/credentials.json` (OAuth client secrets from Google Cloud Console) and run once; a browser will open for consent and save `.secrets/token.json`. Then you can ask e.g. "Send an email to someone@example.com with subject Hello saying thanks."

6. **Optional — LangGraph Studio:** Run the agent in the browser with a local dev server:
   ```bash
   uv sync --extra dev
   uv run langgraph dev
   ```
   Use `uv run` so the dev server runs with the project venv (required for the `email_assistant` package). Then open the Studio URL shown in the terminal. See `docs/RUNNING_AND_TESTING.md` for details.

See `docs/` for architecture, configuration, and running/testing details (filled in as the project is implemented).
