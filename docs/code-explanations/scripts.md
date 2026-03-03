# Explanation: `scripts/`

Detailed walkthrough of the **scripts** in the project root: they run the graph, set up the database, watch Gmail, and debug triage. Each script is explained below in order.

---

## 1. Overview

| Script | Purpose |
|--------|--------|
| **run_agent.py** | Run the graph with question (RUN_MESSAGE) or email (RUN_EMAIL_*) input; handle notify interrupt/resume. |
| **run_mock_email.py** | Run the graph with a mock email (notify/respond/ignore fixture); no Gmail API; HITL demo. |
| **setup_db.py** | Create LangGraph checkpointer tables, run created_at migration, create store table (run once). |
| **watch_gmail.py** | Poll Gmail INBOX, invoke the graph for each new email, track processed ids. |
| **debug_triage.py** | Debug why an email is classified ignore vs respond; check input_router, _is_explicit_request, triage_router. |
| **simulate_gmail_email.py** | Run full flow with mock email (same shape as watcher); no Gmail API; no HITL prompt (auto path). |
| **test_gmail_read.py** | Verify Gmail OAuth and gmail.readonly: list INBOX ids, fetch one message. |

---

## 2. `run_agent.py`

**Purpose:** Run the email assistant graph from the CLI. Loads `.env`, builds/compiles the graph with Postgres or MemorySaver checkpointer, invokes with either **user_message** (question mode) or **email_input** (email mode from env), and on notify interrupt prompts the user to choose respond/ignore and resumes with **Command(resume=...)**.

### Snippets

- **Docstring:** Run Phase 5 graph; question or email mode; Postgres when DATABASE_URL set; notify → interrupt → prompt → resume with Command.
- **Imports:** load_dotenv, MemorySaver, Command, build_email_assistant_graph, postgres_checkpointer.
- **main():** load_dotenv(); thread_id, user_id from env; config = {"configurable": {"thread_id", "user_id"}}; if DATABASE_URL use postgres_checkpointer() and build_email_assistant_graph(checkpointer=checkpointer), else MemorySaver(); _run(graph, config).
- **_run():** If RUN_EMAIL_FROM and RUN_EMAIL_SUBJECT set → input_state = {"email_input": {from, to, subject, body, id}}; else input_state = {"user_message": RUN_MESSAGE or "Hello, how are you?"}. result = graph.invoke(input_state, config). while result.get("__interrupt__"): print pause message, raw = input("Resume with (r)espond or (i)gnore?"), choice = "respond" or "ignore", result = graph.invoke(Command(resume=choice), config). Print last message content, classification_decision, _notify_choice.

---

## 3. `run_mock_email.py`

**Purpose:** Run the graph with a **mock** email (no Gmail API). Uses **get_mock_email(fixture_name)** from **fixtures.mock_emails**; fixture name is **notify** (default), **respond**, or **ignore** (env **MOCK_EMAIL** or first CLI arg). When classification is **notify**, the graph pauses and the script prompts for respond/ignore and resumes with **Command(resume=...)**. When **DATABASE_URL** is set, uses Postgres checkpointer.

### Snippets

- **Docstring:** Test triage and full flow without Gmail; mock email_input from fixtures; notify → interrupt and resume; Postgres when DATABASE_URL set. Example: `MOCK_EMAIL=respond uv run python scripts/run_mock_email.py`.
- **fixture_name:** From os.getenv("MOCK_EMAIL", "notify") or sys.argv[1]; strip().lower().
- **config:** thread_id (default "mock-hitl-1"), user_id.
- **_run():** email_input = get_mock_email(fixture_name); graph.invoke({"email_input": email_input}, config); while result.get("__interrupt__"): prompt and graph.invoke(Command(resume=choice), config); _print_result(result) (classification, _notify_choice, last message).
- **Postgres vs MemorySaver:** Same as run_agent.

---

## 4. `setup_db.py`

**Purpose:** Create LangGraph checkpoint tables and store table in Postgres (run once after setting **DATABASE_URL**). Does **not** create application tables (**users**, **chats**, **messages**, **agent_memory**); those come from **migrations/001_email_assistant_tables.sql**.

### Snippets

- **Docstring:** Run once after DATABASE_URL; creates tables for PostgresSaver and PostgresStore; app tables via 001 migration.
- **main():** load_dotenv(); require DATABASE_URL (exit 1 if missing). with postgres_checkpointer() as cp: cp.setup(). run_checkpoint_created_at_migration(). setup_store(). Print reminders; "Ensure migrations/001_email_assistant_tables.sql has been run for app tables."

---

## 5. `watch_gmail.py`

**Purpose:** Poll Gmail INBOX for messages, invoke the graph with each new email as **email_input**, and track processed message ids so each email is only run once. Requires Gmail OAuth (.secrets/credentials.json, .secrets/token.json) and OPENAI_API_KEY. Uses **list_inbox_message_ids** and **get_message_as_email_input** from **tools.gmail.fetch_emails**.

### Snippets

- **_processed_ids_path():** Default project_root/.gmail_processed_ids.json; override GMAIL_PROCESSED_IDS_FILE.
- **load_processed_ids():** Read JSON, return set(data.get("ids", [])); on error return set().
- **save_processed_ids(ids, max_stored=5000):** Write {"ids": list(ids)[-max_stored:]} to file.
- **main():** load_dotenv(); poll_interval, unread_only, max_results, user_id from env; get_gmail_service() (exit on fail); load_processed_ids(); build graph (Postgres or MemorySaver); _run_loop(service, graph, processed, ...).
- **_run_loop():** while True: ids = list_inbox_message_ids(service, max_results, unread_only). For each message_id not in processed: get_message_as_email_input(service, message_id); if not email_input skip; thread_id = f"gmail-{message_id}"; config = {"configurable": {"thread_id", "user_id"}}; result = graph.invoke({"email_input": email_input}, config); processed.add(message_id); save_processed_ids(processed); print decision, from, subject; if __interrupt__ print note. time.sleep(poll_interval). Catch exceptions and continue.

---

## 6. `debug_triage.py`

**Purpose:** Debug why an email is classified as **ignore** instead of **respond**. Runs **input_router** and **triage_router** locally with a payload from a JSON file or default **MOCK_EMAIL_RESPOND**. Prints: raw email_input keys/subject/body; normalized email after input_router; **_is_explicit_request** pattern matches and result; **triage_router** output (classification_decision); and a Studio run-input tip.

### Snippets

- **get_payload():** If sys.argv[1] given, read JSON file; if has "email_input" use as-is else {"email_input": data}. Else {"email_input": MOCK_EMAIL_RESPOND}.
- **main():** payload = get_payload(); state_in = {"messages": [], "email_input": payload["email_input"]}; updates = input_router(state_in); state_after_router = {**state_in, **updates}. Print raw keys, subject, body. If email_input missing after router, print Studio tip. Print normalized keys, subject, body. Print _is_explicit_request patterns and match result; call _is_explicit_request; call triage_router(state_after_router); print classification_decision; if not "respond" print UNEXPECTED tip. Print Studio run input example JSON.

---

## 7. `simulate_gmail_email.py`

**Purpose:** Run the full graph flow with a **mock** email in the same shape the Gmail watcher would pass (from **get_mock_email**). No Gmail API or OAuth. Single invoke only—no HITL prompt loop. **SIMULATE_EMAIL** env or first CLI arg: notify (default), respond, ignore.

### Snippets

- **main():** fixture_name from SIMULATE_EMAIL or sys.argv[1]; thread_id, user_id, config; email_input = get_mock_email(fixture_name); print From/To/Subject/Body. Build graph; _simulate(graph, config, email_input).
- **_simulate():** result = graph.invoke({"email_input": email_input}, config); print classification_decision; if notify print _notify_choice; if respond print that prepare_messages/response_agent/mark_as_read ran; if ignore print graph ended. Print last message. No while __interrupt__ loop.

---

## 8. `test_gmail_read.py`

**Purpose:** Verify Gmail OAuth and **gmail.readonly** scope by listing INBOX message ids (recent 5) and fetching the first message as **email_input**. Run from repo root: **uv run python scripts/test_gmail_read.py**.

### Snippets

- **main():** load_dotenv(); get_gmail_service() (on fail print and return); list_inbox_message_ids(service, max_results=5, unread_only=False) (on fail print and return); print ids; mid = ids[0]; get_message_as_email_input(service, mid); if not email_input print and return; print subject, from; "Gmail read test OK. You can run the watcher: uv run python scripts/watch_gmail.py". sys.path.insert for project root import.

---

## 9. Flow summary (scripts)

1. **One-time setup:** Run setup_db.py (with DATABASE_URL) to create checkpointer tables, run 002 migration, create store table. Run migrations/001_email_assistant_tables.sql for app tables.
2. **Question or email (CLI):** run_agent.py — RUN_MESSAGE or RUN_EMAIL_*; on notify, prompt and Command(resume=...).
3. **Mock email:** run_mock_email.py — MOCK_EMAIL=notify|respond|ignore; same interrupt/resume. simulate_gmail_email.py — same fixtures, single invoke, no resume loop.
4. **Gmail watcher:** watch_gmail.py — poll INBOX, invoke per new id, processed ids file.
5. **Debug:** debug_triage.py — payload from file or MOCK_EMAIL_RESPOND; input_router + triage_router; print normalized input, _is_explicit_request, classification; Studio tip.
6. **Gmail auth:** test_gmail_read.py — list 5 ids, fetch first as email_input; confirms OAuth and gmail.readonly.

---

## 10. Related files

- **Graph:** src/email_assistant/email_assistant_hitl_memory_gmail.py (build_email_assistant_graph).
- **Checkpointer:** src/email_assistant/db/checkpointer.py (postgres_checkpointer), db/studio_checkpointer.py.
- **Store / migrations:** src/email_assistant/db/store.py (setup_store), migrations/001, 002.
- **Mock emails:** src/email_assistant/fixtures/mock_emails.py (get_mock_email).
- **Fetch emails:** src/email_assistant/tools/gmail/fetch_emails.py (list_inbox_message_ids, get_message_as_email_input).

For graph and checkpointer details, see **email_assistant_hitl_memory_gmail.md** and **db_checkpointer.md**.
