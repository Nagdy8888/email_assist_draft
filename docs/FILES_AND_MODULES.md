# Files and modules

File-by-file guide to the codebase.

## Layout

- **Phase 5 entry:** `src/email_assistant/email_assistant_hitl_memory_gmail.py` — one agent: input_router → Email Assistant subgraph or prepare_messages → Response subgraph → mark_as_read. Two subagents (compiled subgraphs as nodes).
- **State/schemas**: `schemas.py` — State (includes user_message, question), StateInput, RouterSchema.
- **Nodes**: `nodes/input_router.py`; `nodes/triage.py`; `nodes/triage_interrupt.py`; `nodes/prepare_messages.py` — inject reply context before Response subgraph; `nodes/mark_as_read.py`. Response subgraph is built in `simple_agent.py` (build_response_subgraph).

## Tree


| Path                                                       | Purpose                                                            |
| ---------------------------------------------------------- | ------------------------------------------------------------------ |
| `src/email_assistant/__init__.py`                          | Package init, version                                              |
| `src/email_assistant/email_assistant_hitl_memory_gmail.py` | Entry: build + compile graph                                       |
| `src/email_assistant/simple_agent.py`                      | Response subgraph: build_response_subgraph() (chat, tools, persist_messages); alias build_simple_graph |
| `src/email_assistant/prompts.py`                           | SIMPLE_AGENT_SYSTEM_PROMPT; get_agent_system_prompt_with_tools()    |
| `src/email_assistant/schemas.py`                           | MessagesState; State, StateInput, RouterSchema (Phase 5)             |
| `src/email_assistant/nodes/input_router.py`                | input_router; normalize email_input (set _source='gmail' when from Gmail), user_message |
| `src/email_assistant/nodes/triage.py`                      | triage_router; LLM + RouterSchema                                      |
| `src/email_assistant/nodes/triage_interrupt.py`            | triage_interrupt_handler; interrupt for notify; exits to subgraph END |
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
| `src/email_assistant/db/checkpointer.py`                   | postgres_checkpointer(); PostgresSaver + setup()                    |
| `src/email_assistant/db/persist_messages.py`              | persist_messages(); write chats/messages after run                 |
| `scripts/run_agent.py`                                     | Run agent; Postgres + persist when DATABASE_URL set                |
| `scripts/watch_gmail.py`                                   | Gmail watcher: poll INBOX, invoke graph per new email; processed ids in .gmail_processed_ids.json |
| `scripts/setup_db.py`                                     | One-time: checkpointer.setup() and store.setup()                   |
| `migrations/001_email_assistant_tables.sql`                | App schema: users, chats, messages, agent_memory                   |
| `langgraph.json`                                          | LangGraph Studio: graphs and env; `langgraph dev` uses this        |
| `migrations/`                                              | DB schema (SQL in Phase 3)                                         |
| `notebooks/`                                               | Notebook (Phase 7)                                                 |
| `tests/`                                                   | Tests                                                              |


