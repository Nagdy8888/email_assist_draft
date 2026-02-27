# Files and modules

File-by-file guide to the codebase.

## Layout

- **Phase 4 entry:** `src/email_assistant/simple_agent.py` — graph with tool loop (chat → tools → chat → persist); send_email_tool, question_tool, done_tool.
- **Full graph entry (later):** `src/email_assistant/email_assistant_hitl_memory_gmail.py` — builds and compiles the full graph.
- **State/schemas**: `schemas.py` — State, StateInput, RouterSchema, UserPreferences.
- **Prompts**: `prompts.py` — triage, agent, memory-update prompts; `tools/gmail/prompt_templates.py` — Gmail tools prompt.
- **Memory**: `memory.py` — get_memory, update_memory (store-agnostic).
- **Utils**: `utils.py` — parse_gmail, format_gmail_markdown, format_for_display.
- **Nodes**: `nodes/` — input_router, triage, triage_interrupt, response_agent, mark_as_read.
- **Tools**: `tools/` — get_tools; `tools/gmail/` — send_email, fetch_emails, mark_as_read, calendar; `tools/common.py` — Question, Done.
- **DB**: `db/store.py` — PostgresStore; `db/checkpointer.py` — PostgresSaver; `db/persist_messages.py` — persist chats/messages.

## Tree


| Path                                                       | Purpose                                                            |
| ---------------------------------------------------------- | ------------------------------------------------------------------ |
| `src/email_assistant/__init__.py`                          | Package init, version                                              |
| `src/email_assistant/email_assistant_hitl_memory_gmail.py` | Entry: build + compile graph                                       |
| `src/email_assistant/simple_agent.py`                      | Phase 4: graph with tool loop (chat, tools, persist_messages)       |
| `src/email_assistant/prompts.py`                           | SIMPLE_AGENT_SYSTEM_PROMPT; get_agent_system_prompt_with_tools()    |
| `src/email_assistant/schemas.py`                           | MessagesState; StateInput, RouterSchema (later)                     |
| `src/email_assistant/utils.py`                             | parse_gmail, format_gmail_markdown (later)                          |
| `src/email_assistant/memory.py`                            | get_memory, update_memory (Phase 6)                                 |
| `src/email_assistant/nodes/*.py`                           | input_router, triage, response_agent, etc. (Phase 5+)              |
| `src/email_assistant/tools/__init__.py`                    | get_tools() → send_email_tool, question_tool, done_tool             |
| `src/email_assistant/tools/common.py`                      | question_tool, done_tool                                            |
| `src/email_assistant/tools/gmail/send_email.py`            | send_email_tool; send_new_email() (Phase 4)                         |
| `src/email_assistant/tools/gmail/auth.py`                  | get_credentials(), get_gmail_service(); OAuth                       |
| `src/email_assistant/tools/gmail/prompt_templates.py`      | get_gmail_tools_prompt(), GMAIL_TOOLS_PROMPT                        |
| `src/email_assistant/db/store.py`                          | PostgresStore; setup_store()                                       |
| `src/email_assistant/db/checkpointer.py`                   | postgres_checkpointer(); PostgresSaver + setup()                    |
| `src/email_assistant/db/persist_messages.py`              | persist_messages(); write chats/messages after run                 |
| `scripts/run_agent.py`                                     | Run agent; Postgres + persist when DATABASE_URL set                |
| `scripts/setup_db.py`                                     | One-time: checkpointer.setup() and store.setup()                   |
| `migrations/001_email_assistant_tables.sql`                | App schema: users, chats, messages, agent_memory                   |
| `langgraph.json`                                          | LangGraph Studio: graphs and env; `langgraph dev` uses this        |
| `migrations/`                                              | DB schema (SQL in Phase 3)                                         |
| `notebooks/`                                               | Notebook (Phase 7)                                                 |
| `tests/`                                                   | Tests                                                              |


