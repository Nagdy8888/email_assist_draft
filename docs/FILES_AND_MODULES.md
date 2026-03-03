# Files and modules

File-by-file guide to the codebase.

## Layout

- **Phase 5 entry:** `src/email_assistant/email_assistant_hitl_memory_gmail.py` — one agent: input_router → Email Assistant subgraph or prepare_messages → Response subgraph → mark_as_read. Two subagents (compiled subgraphs as nodes).
- **State/schemas**: `schemas.py` — State (includes user_message, question), StateInput, RouterSchema, NotifyChoiceSchema.
- **Fixtures**: `fixtures/mock_emails.py` — mock email_input payloads (notify, respond, ignore) for testing without Gmail API.
- **Nodes**: `nodes/input_router.py`; `nodes/triage.py`; `nodes/triage_interrupt.py` (when notify, calls `interrupt()` for HITL — user chooses respond or ignore); `nodes/prepare_messages.py` — inject reply context before Response subgraph; `nodes/mark_as_read.py`. Response subgraph is built in `simple_agent.py` (build_response_subgraph).

## Tree


| Path                                                       | Purpose                                                            |
| ---------------------------------------------------------- | ------------------------------------------------------------------ |
| `src/email_assistant/__init__.py`                          | Package init, version                                              |
| `src/email_assistant/email_assistant_hitl_memory_gmail.py` | Entry: build + compile graph                                       |
| `src/email_assistant/simple_agent.py`                      | Response subgraph: build_response_subgraph() (chat, tools, persist_messages); alias build_simple_graph |
| `src/email_assistant/prompts.py`                           | SIMPLE_AGENT_SYSTEM_PROMPT; get_agent_system_prompt_with_tools()    |
| `src/email_assistant/schemas.py`                           | MessagesState; State, StateInput, RouterSchema, NotifyChoiceSchema (Phase 5) |
| `src/email_assistant/fixtures/mock_emails.py`              | MOCK_EMAIL_NOTIFY, MOCK_EMAIL_RESPOND, MOCK_EMAIL_IGNORE; get_mock_email(); for run_mock_email and simulation |
| `src/email_assistant/nodes/input_router.py`                | input_router; _normalize_email_input (unwrap double-nested email_input, flat or Gmail API); normalize email_input (set _source='gmail' when from Gmail), user_message |
| `src/email_assistant/nodes/triage.py`                      | triage_router; _is_explicit_request() override for request phrases (e.g. "send me the report"); LLM + RouterSchema |
| `src/email_assistant/nodes/triage_interrupt.py`            | triage_interrupt_handler; when notify, calls interrupt() — graph pauses until user resumes with Command(resume="respond") or Command(resume="ignore") |
| `src/email_assistant/nodes/prepare_messages.py`            | prepare_messages; inject reply context when email_id/email_input set |
| `src/email_assistant/nodes/mark_as_read.py`                 | mark_as_read_node; Gmail mark_as_read when email_id                    |
| `src/email_assistant/tools/gmail/send_email.py`            | send_new_email, send_reply_email, send_email_tool (email_id for reply) |
| `src/email_assistant/tools/gmail/mark_as_read.py`          | mark_as_read(email_id)                                                 |
| `src/email_assistant/tools/__init__.py`                    | get_tools() → send_email_tool, question_tool, done_tool                 |
| `src/email_assistant/tools/common.py`                      | question_tool, done_tool                                                |
| `src/email_assistant/tools/gmail/auth.py`                  | get_credentials(), get_gmail_service(); OAuth                            |
| `src/email_assistant/tools/gmail/fetch_emails.py`         | list_inbox_message_ids(); get_message_as_email_input(); fetch_recent_inbox(); used by watch_gmail |
| `src/email_assistant/tools/gmail/prompt_templates.py`      | get_gmail_tools_prompt(), GMAIL_TOOLS_PROMPT                        |
| `src/email_assistant/db/store.py`                          | PostgresStore; setup_store()                                       |
| `src/email_assistant/db/checkpointer.py`                   | postgres_checkpointer() (search_path=email_assistant); run_checkpoint_created_at_migration() |
| `src/email_assistant/db/studio_checkpointer.py`           | generate_checkpointer() async context manager for LangGraph Studio; Supabase in email_assistant schema |
| `src/email_assistant/db/persist_messages.py`              | persist_messages(); write chats/messages after run                 |
| `scripts/run_agent.py`                                     | Run agent; Postgres + persist when DATABASE_URL set                |
| `scripts/run_mock_email.py`                                | Run graph with mock email; on notify interrupt prompts (r)espond or (i)gnore and resumes with Command(resume=...); uses Supabase checkpointer when DATABASE_URL set |
| `scripts/simulate_gmail_email.py`                          | Simulate graph receiving real Gmail email: same flow, mock payload; prints steps (triage, notify choice); SIMULATE_EMAIL fixture |
| `scripts/watch_gmail.py`                                   | Gmail watcher: poll INBOX, invoke graph per new email; processed ids in .gmail_processed_ids.json |
| `scripts/setup_db.py`                                     | One-time: checkpointer.setup(), run_checkpoint_created_at_migration(), store.setup() |
| `migrations/001_email_assistant_tables.sql`                | App schema: users, chats, messages, agent_memory                   |
| `migrations/002_checkpoint_created_at.sql`                 | Add created_at TIMESTAMPTZ to checkpoint tables in email_assistant schema |
| `langgraph.json`                                          | LangGraph Studio: graphs, env, checkpointer.path (Supabase)        |
| `docs/PROJECT_SUMMARY.md`                                 | Summary of what was done from project start to now (phases, refactor, Gmail, fixes) |
| `docs/guide/DOCS_INDEX.md`                                | Index of the 10-file guide (01_OVERVIEW … 10_QUICK_REFERENCE) |
| `docs/guide/01_OVERVIEW.md` … `docs/guide/10_QUICK_REFERENCE.md` | Structured guide: overview, structure, architecture, triage, DB, config, prompts, running, what we did, quick reference |
| `docs/code-explanations/README.md`                               | Index of file-by-file code explanations |
| `docs/code-explanations/email_assistant_hitl_memory_gmail.md`    | Detailed explanation of entry point: graph build, subgraphs, routing, checkpointer |
| `docs/code-explanations/simple_agent.md`                        | Response subgraph: chat, tools loop, persist_messages, build_response_subgraph |
| `docs/code-explanations/schemas.md`                             | State, StateInput, MessagesState, ClassificationDecision, RouterSchema, NotifyChoiceSchema |
| `docs/code-explanations/prompts.md`                             | Triage, agent, notify-choice prompts; get_triage_*, get_agent_system_prompt_*, constants |
| `docs/code-explanations/nodes_input_router.md`                  | input_router node: normalize input, email_input vs question path, _normalize_email_input |
| `docs/code-explanations/nodes_triage.md`                       | triage_router node: classify ignore/notify/respond, RouterSchema, _is_explicit_request |
| `docs/code-explanations/nodes_triage_interrupt.md`             | triage_interrupt_handler: interrupt() for notify HITL, _notify_choice, NOTIFY_INTERRUPT_MESSAGE |
| `docs/code-explanations/nodes_prepare_messages.md`            | prepare_messages: inject reply context (email_id, from/subject/body) before Response subgraph |
| `docs/code-explanations/nodes_mark_as_read.md`                | mark_as_read_node: call Gmail mark_as_read when email_id set; no-op otherwise |
| `docs/code-explanations/tools_init.md`                        | tools/__init__.py: get_tools(include_gmail), send_email_tool, question_tool, done_tool |
| `docs/code-explanations/tools_common.md`                     | tools/common.py: question_tool, done_tool (@tool, docstrings, return values) |
| `docs/code-explanations/tools_gmail_auth.md`                 | tools/gmail/auth.py: SCOPES, get_credentials (token/refresh/flow), get_gmail_service |
| `docs/code-explanations/tools_gmail_send_email.md`           | tools/gmail/send_email.py: send_email_tool, send_new_email, send_reply_email |
| `docs/code-explanations/tools_gmail_mark_as_read.md`        | tools/gmail/mark_as_read.py: mark_as_read (Gmail modify, removeLabelIds UNREAD) |
| `docs/code-explanations/tools_gmail_fetch_emails.md`        | tools/gmail/fetch_emails.py: list_inbox_message_ids, get_message_as_email_input, fetch_recent_inbox |
| `docs/code-explanations/tools_gmail_prompt_templates.md`   | tools/gmail/prompt_templates.py: get_gmail_tools_prompt, GMAIL_TOOLS_PROMPT (Tools section for agent) |
| `docs/code-explanations/db_checkpointer.md`                | db/checkpointer.py: postgres_checkpointer, run_checkpoint_created_at_migration, get_checkpointer |
| `docs/code-explanations/db_studio_checkpointer.md`          | db/studio_checkpointer.py: generate_checkpointer (async, AsyncPostgresSaver, setup()) |
| `docs/code-explanations/db_store.md`                       | db/store.py: postgres_store (PostgresStore), setup_store (create store table) |
| `docs/code-explanations/db_persist_messages.md`           | db/persist_messages.py: persist_messages (users/chats/messages sync), thread_id_to_chat_id |
| `docs/code-explanations/fixtures_mock_emails.md`         | fixtures/mock_emails.py: MOCK_EMAIL_NOTIFY/RESPOND/IGNORE, get_mock_email (testing/HITL demos) |
| `docs/code-explanations/scripts.md`                      | scripts/: run_agent, run_mock_email, setup_db, watch_gmail, debug_triage, simulate_gmail_email, test_gmail_read |
| `docs/code-explanations/config.md`                      | Config: .env.example, langgraph.json (graphs, checkpointer, env) |
| `docs/code-explanations/migrations.md`                  | migrations/: 000 drop schema, 001 app tables, 002 checkpoint created_at |
| `migrations/`                                              | DB schema (SQL in Phase 3)                                         |
| `notebooks/`                                               | Notebook (Phase 7)                                                 |
| `tests/`                                                   | Tests                                                              |


