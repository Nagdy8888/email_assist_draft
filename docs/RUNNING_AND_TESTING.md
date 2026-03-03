# Running and testing

How to run and test the agent.

## Phase 5: Email assistant (question + email mode)

1. **Environment**
   - Copy `.env.example` to `.env`.
   - Set `OPENAI_API_KEY` (required). Optionally set `OPENAI_MODEL` (default `gpt-4o`).
   - For LangSmith tracing: set `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY`, and optionally `LANGCHAIN_PROJECT`.
   - For Gmail (send/reply, mark as read): `.secrets/credentials.json` and `.secrets/token.json` (see CONFIGURATION.md).

2. **Run (question mode)**
   - From repo root with venv activated:
     ```bash
     uv sync
     uv run python scripts/run_agent.py
     ```
   - Default message is "Hello, how are you?" or set `RUN_MESSAGE` in `.env`.

3. **Run (email mode)**
   - Set env vars and run the same script:
     ```bash
     set RUN_EMAIL_FROM=sender@example.com
     set RUN_EMAIL_TO=you@example.com
     set RUN_EMAIL_SUBJECT=Test
     set RUN_EMAIL_BODY=Body text
     uv run python scripts/run_agent.py
     ```
   - Optional: `RUN_EMAIL_ID` (Gmail message id) for triage context. The graph will triage (ignore/notify/respond). When classification is **notify**, the graph **pauses** (interrupt) and prompts you to choose respond or ignore; then resume with `Command(resume="respond")` or `Command(resume="ignore")`.

4. **Multi-turn**
   - Use the same `thread_id` in config for multi-turn. When classification is **notify**, the graph pauses (interrupt); run_agent.py prompts you to choose respond or ignore and then resumes with Command(resume=...).

5. **Phase 3 — with Postgres**
   - Set `DATABASE_URL` in `.env`. Run migrations and `uv run python scripts/setup_db.py`. Then run the agent; it uses the Postgres checkpointer and persists messages via the Response subgraph.
   - For **mock-email testing** and Studio, set `DATABASE_URL` to your **Supabase Postgres** connection string (Supabase dashboard → Project Settings → Database → Connection string). Run `uv run python scripts/setup_db.py` once so LangGraph checkpointer tables exist in the `email_assistant` schema; after that, checkpoint data is stored in Supabase (CLI scripts and Studio both use it when configured).

## Mock email testing (no Gmail API)

To test triage and the full flow without Gmail API, use mock emails. When classification is **notify**, the graph **pauses** (interrupt) and the script prompts you to choose (r)espond or (i)gnore, then resumes with Command(resume=...).

1. **Optional:** Set `DATABASE_URL` to your Supabase Postgres connection string and run `uv run python scripts/setup_db.py` once so checkpoint data is stored in Supabase.
2. Run:
   ```bash
   uv run python scripts/run_mock_email.py
   ```
   Default fixture is **notify**. The graph may pause at interrupt; the script then prompts "Resume with (r)espond or (i)gnore?" and resumes with Command(resume=...) until the run completes.
3. Use another fixture: `MOCK_EMAIL=respond uv run python scripts/run_mock_email.py` or `uv run python scripts/run_mock_email.py ignore`.

## Simulating real Gmail delivery (no Gmail API)

To see **exactly what happens** when the graph receives a real email from the Gmail API — same flow (input_router → triage → notify/respond/ignore; when notify, graph pauses for you to choose respond or ignore) — without calling Gmail:

1. **Run the simulation script** (uses mock payload with the same shape the watcher would pass):
   ```bash
   uv run python scripts/simulate_gmail_email.py
   ```
   Default fixture is **notify**. The script prints: simulated email headers, triage result, and for notify the interrupt (you would resume with respond/ignore in a full run). Use another fixture: `SIMULATE_EMAIL=respond uv run python scripts/simulate_gmail_email.py` or `uv run python scripts/simulate_gmail_email.py ignore`.

## Debugging triage (ignore vs respond)

If an email that should be **respond** is classified as **ignore** in Studio:

1. **Run the debug script** to verify triage locally with the same payload:
   ```bash
   uv run python scripts/debug_triage.py
   ```
   This uses `MOCK_EMAIL_RESPOND`, runs `input_router` then `triage_router`, and prints: raw input keys, normalized `email_input`, whether `_is_explicit_request` matched, and the final `classification_decision`. If the script prints **respond** but Studio shows **ignore**, the Studio server may be using old code (restart `langgraph dev`) or the run input in Studio may not be `email_input` (e.g. using the chat box sends `user_message` instead).

2. **Debug the exact Studio payload:** Save the run input JSON Studio uses to a file (e.g. `payload.json`) and run:
   ```bash
   uv run python scripts/debug_triage.py payload.json
   ```
   The script accepts `{"email_input": {...}}` or a bare `{...}` object as the file content.

3. **Studio run input:** Ensure you set the **run input** (e.g. "Edit run input") to JSON with key `email_input`, not a chat message. Example: `{"email_input": {"from": "...", "to": "...", "subject": "...", "body": "..."}}`.

**Same flow in Studio:** Paste an `email_input` payload in Studio (e.g. from `src/email_assistant/fixtures/mock_emails.py`: `MOCK_EMAIL_NOTIFY`, `MOCK_EMAIL_RESPOND`, `MOCK_EMAIL_IGNORE`). The graph runs the same steps; when classification is **notify**, the graph **pauses** (interrupt). In Studio you can resume by sending a resume command with value `"respond"` or `"ignore"` (see Studio UI for interrupt/resume).

3. **Optional:** Set `DATABASE_URL` so checkpoint data is stored in Supabase. Studio uses the same Supabase checkpointer when `langgraph.json` is configured with `checkpointer.path` (see below).

## LangGraph Studio (local)

Run the agent in [LangGraph Studio](https://smith.langchain.com/studio) with a local dev server:

1. **Install and start** from the project root:
   ```bash
   uv sync --extra dev
   uv run langgraph dev
   ```
   - API: `http://127.0.0.1:2024`
   - Studio UI: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`

2. **If Studio shows "Failed to initialize Studio" / "TypeError: Failed to fetch"**
   - **Graph failed to load:** The entry point `email_assistant` is compiled without a checkpointer in code; the Studio server injects the checkpointer from `langgraph.json` when `checkpointer.path` is set. Ensure `DATABASE_URL` is set if you use the Supabase checkpointer.
   - **Chrome 142+ (Private Network Access):** The browser may block the Studio page (HTTPS) from talking to your local API (HTTP). Fix:
     1. Open `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`
     2. Click the **lock** or **site info** icon in the address bar
     3. Find **"Local network access"** (or "Insecure content" / site settings)
     4. Set it to **Allow**, then reload the page
   - **Alternative:** Run with a tunnel so the API is reachable over HTTPS:
     ```bash
     uv run langgraph dev --tunnel
     ```
     (Requires `langgraph-cli>=0.2.6`; uses Cloudflare Tunnel.)
   - **Safari / Brave:** Prefer `langgraph dev --tunnel` or use Chrome/Edge.

3. **Graph:** `langgraph.json` exposes a single graph **email_assistant** (one agent with two subagents: Email Assistant, Response). Question mode = invoke with `{"user_message": "Hello"}`; email mode = invoke with `{"email_input": {...}}`.

4. **Input format**
   - Question mode: `{"user_message": "Hello"}` or `{"messages": [{"role": "human", "content": "Hello"}]}`.
   - Email mode (triage path): `{"email_input": {"from": "...", "to": "...", "subject": "...", "body": "...", "id": "optional-gmail-id"}}`. **You must send `email_input` to run triage.** If you only type a message in the chat, that goes as `user_message` and the graph runs the question path (no classification). To test triage in Studio, set the run input to a JSON object with `email_input` (e.g. copy `MOCK_EMAIL_RESPOND` from `src/email_assistant/fixtures/mock_emails.py`). If the run input is double-wrapped (e.g. `{"email_input": {"email_input": {...}}}`), the input_router unwraps it so the email fields are preserved.
   - **Resuming from notify interrupt:** When the run pauses (e.g. after classifying an email as **notify**), Studio shows the interrupt. Use the resume control in the Studio UI and send the value **respond** or **ignore** so the graph continues.

5. **Checkpoints in Supabase**
   - Set `DATABASE_URL` in `.env` to your Supabase Postgres connection string. Run `uv run python scripts/setup_db.py` once so checkpoint tables exist in the **email_assistant** schema.
   - Restart `langgraph dev` **after** changing `.env` so the server loads `DATABASE_URL` and injects the checkpointer. Checkpoints are stored in the **email_assistant** schema (tables: `checkpoint_migrations`, `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`), not in `public`.
   - **Checkpoint tables empty / last run not stored?**
     1. **Schema:** Query the correct schema: `SELECT thread_id, checkpoint_id, created_at FROM email_assistant.checkpoints ORDER BY created_at DESC LIMIT 10;` (Supabase SQL editor or `psql`). If you query `public.checkpoints` you will see no rows.
     2. **Studio:** Ensure `DATABASE_URL` is in `.env` and **restart** `langgraph dev` after any change to `.env`. The server reads env at startup; if it started without `DATABASE_URL`, it may not use the Postgres checkpointer and nothing is stored.
     3. **Verify with CLI:** Run a single invoke from the CLI so you know the thread_id, then check the DB:  
        `set THREAD_ID=test-checkpoint` then `uv run python scripts/run_mock_email.py respond`  
        Then in SQL: `SELECT * FROM email_assistant.checkpoints WHERE thread_id = 'test-checkpoint';`  
        If CLI writes rows but Studio still doesn’t, check the `langgraph dev` terminal for errors when loading the checkpointer (e.g. "DATABASE_URL is required").

6. **Config:** Use the project venv so `email_assistant` is importable (`uv run langgraph dev`). Set `DATABASE_URL` in `.env` to use the Supabase checkpointer (same as CLI); `langgraph.json` points to `db/studio_checkpointer.py:generate_checkpointer`.

## Automatic Gmail ingestion (watcher)

To have the agent **automatically see any real email** that arrives in your Gmail INBOX, run the watcher in a **separate terminal** so you can keep LangGraph Studio running at the same time:

- **Terminal 1:** Keep `uv run langgraph dev` running (for Studio in the browser).
- **Terminal 2:** Run the watcher:
  ```bash
  uv run python scripts/watch_gmail.py
  ```

The watcher runs the graph in its own process (it does not use the Studio server). Both can run together: Studio for manual invokes; the watcher for automatic Gmail ingestion. When classification is **notify**, the graph pauses (interrupt); the watcher script would need to resume with a choice (see scripts/watch_gmail.py for interrupt handling).

**If the graph does not see your emails:** Run the Gmail read test first: `uv run python scripts/test_gmail_read.py`. It checks OAuth and INBOX list/get. If you see **403 Insufficient Permission** or "insufficient authentication scopes", your token was created without `gmail.readonly`. **Fix:** Delete (or rename) `.secrets/token.json` and run the test again; the OAuth flow will open a browser and request access — approve so the new token includes read (and modify) scope. If you have no **unread** emails, set `GMAIL_UNREAD_ONLY=0` so the watcher fetches recent inbox messages.

Prerequisites: Gmail OAuth (`.secrets/credentials.json`, `.secrets/token.json`) and `OPENAI_API_KEY`. The script polls Gmail (default: unread INBOX every 60s), invokes the graph for each new message, and stores processed message ids in `.gmail_processed_ids.json` so each email is only handled once. Optional env: `GMAIL_POLL_INTERVAL`, `GMAIL_UNREAD_ONLY`, `GMAIL_MAX_RESULTS`, `GMAIL_PROCESSED_IDS_FILE` (see CONFIGURATION.md). Each email gets thread_id `gmail-{message_id}`. When classification is **notify**, the graph pauses (interrupt); the watcher may need to resume with respond/ignore (check watch_gmail.py for interrupt handling).

## When does the agent see an email sent to me in Gmail?

The agent runs **classification (triage) and the full flow** whenever an email is passed into the graph as **`email_input`**:

- **Automatic:** Run `scripts/watch_gmail.py` to poll Gmail and feed each new (unread) email into the graph (see section above).
- **Manual:** Invoke the graph with `email_input` set (e.g. run_agent.py, Studio, or your own script). Without the watcher, the graph does not poll Gmail by itself.
