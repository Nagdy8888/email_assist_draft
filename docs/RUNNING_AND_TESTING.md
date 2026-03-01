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
   - Optional: `RUN_EMAIL_ID` (Gmail message id) for triage context. The graph will triage (ignore/notify/respond); on **notify** the graph pauses and you can resume with `Command(resume="respond")` or `Command(resume="ignore")` (same `thread_id` in config).

4. **Multi-turn and HITL**
   - Use the same `thread_id` in config for multi-turn. When the graph hits an interrupt (notify path), the result contains `__interrupt__`; resume by invoking again with `graph.invoke(Command(resume="respond"), config=config)` (or `"ignore"`).

5. **Phase 3 — with Postgres**
   - Set `DATABASE_URL` in `.env`. Run migrations and `uv run python scripts/setup_db.py`. Then run the agent; it uses the Postgres checkpointer and persists messages via the Response subgraph.

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
   - **Graph failed to load:** Ensure the graph is built **without** a custom checkpointer when served by `langgraph dev` (the API provides its own). The entry point `email_assistant` is compiled with no checkpointer; `run_agent.py` passes one explicitly.
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
   - Email mode: `{"email_input": {"from": "...", "to": "...", "subject": "...", "body": "...", "id": "optional-gmail-id"}}`.

5. **Config:** Use the project venv so `email_assistant` is importable (`uv run langgraph dev`).

## Automatic Gmail ingestion (watcher)

To have the agent **automatically see any real email** that arrives in your Gmail INBOX, run the watcher in a **separate terminal** so you can keep LangGraph Studio running at the same time:

- **Terminal 1:** Keep `uv run langgraph dev` running (for Studio in the browser).
- **Terminal 2:** Run the watcher:
  ```bash
  uv run python scripts/watch_gmail.py
  ```

The watcher runs the graph in its own process (it does not use the Studio server). Both can run together: Studio for manual invokes and resuming notify; the watcher for automatic Gmail ingestion.

**If the graph does not see your emails:** Run the Gmail read test first: `uv run python scripts/test_gmail_read.py`. It checks OAuth and INBOX list/get. If you see **403 Insufficient Permission** or "insufficient authentication scopes", your token was created without `gmail.readonly`. **Fix:** Delete (or rename) `.secrets/token.json` and run the test again; the OAuth flow will open a browser and request access — approve so the new token includes read (and modify) scope. If you have no **unread** emails, set `GMAIL_UNREAD_ONLY=0` so the watcher fetches recent inbox messages.

Prerequisites: Gmail OAuth (`.secrets/credentials.json`, `.secrets/token.json`) and `OPENAI_API_KEY`. The script polls Gmail (default: unread INBOX every 60s), invokes the graph for each new message, and stores processed message ids in `.gmail_processed_ids.json` so each email is only handled once. Optional env: `GMAIL_POLL_INTERVAL`, `GMAIL_UNREAD_ONLY`, `GMAIL_MAX_RESULTS`, `GMAIL_PROCESSED_IDS_FILE` (see CONFIGURATION.md). Each email gets thread_id `gmail-{message_id}`. On **notify** the graph pauses; resume with `Command(resume="respond")` or `Command(resume="ignore")` using that thread_id (e.g. from Studio or run_agent.py).

## When does the agent see an email sent to me in Gmail?

The agent runs **classification (triage) and the full flow** whenever an email is passed into the graph as **`email_input`**:

- **Automatic:** Run `scripts/watch_gmail.py` to poll Gmail and feed each new (unread) email into the graph (see section above).
- **Manual:** Invoke the graph with `email_input` set (e.g. run_agent.py, Studio, or your own script). Without the watcher, the graph does not poll Gmail by itself.
