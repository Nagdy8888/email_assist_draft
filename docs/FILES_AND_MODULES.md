# Files and modules

File-by-file guide to the codebase.

## Layout

- **Phase 2 entry:** `src/email_assistant/simple_agent.py` — builds and compiles the simple graph (START → chat → END); used by `run_agent.py`.
- **Full graph entry (later):** `src/email_assistant/email_assistant_hitl_memory_gmail.py` — builds and compiles the full graph.
- **State/schemas**: `schemas.py` — State, StateInput, RouterSchema, UserPreferences.
- **Prompts**: `prompts.py` — triage, agent, memory-update prompts; `tools/gmail/prompt_templates.py` — Gmail tools prompt.
- **Memory**: `memory.py` — get_memory, update_memory (store-agnostic).
- **Utils**: `utils.py` — parse_gmail, format_gmail_markdown, format_for_display.
- **Nodes**: `nodes/` — input_router, triage, triage_interrupt, response_agent, mark_as_read.
- **Tools**: `tools/` — get_tools; `tools/gmail/` — send_email, fetch_emails, mark_as_read, calendar; `tools/common.py` — Question, Done.
- **DB**: `db/store.py` — memory store; `db/checkpointer.py` — PostgresSaver.

## Tree


| Path                                                       | Purpose                                                            |
| ---------------------------------------------------------- | ------------------------------------------------------------------ |
| `src/email_assistant/__init__.py`                          | Package init, version                                              |
| `src/email_assistant/email_assistant_hitl_memory_gmail.py` | Entry: build + compile graph                                       |
| `src/email_assistant/simple_agent.py`                      | Phase 2: simple graph (chat node), build_simple_graph()             |
| `src/email_assistant/schemas.py`                           | MessagesState (Phase 2), StateInput, RouterSchema (later)          |
| `src/email_assistant/prompts.py`                           | SIMPLE_AGENT_SYSTEM_PROMPT (Phase 2), triage/agent prompts (later) |
| `src/email_assistant/utils.py`                             | parse_gmail, format_gmail_markdown, format_for_display             |
| `src/email_assistant/memory.py`                            | get_memory, update_memory                                          |
| `src/email_assistant/nodes/input_router.py`                | input_router: email vs question                                    |
| `src/email_assistant/nodes/triage.py`                      | triage_router                                                      |
| `src/email_assistant/nodes/triage_interrupt.py`            | triage_interrupt_handler                                           |
| `src/email_assistant/nodes/response_agent.py`              | Response subgraph                                                  |
| `src/email_assistant/nodes/mark_as_read.py`                | mark_as_read_node                                                  |
| `src/email_assistant/tools/__init__.py`                    | get_tools(include_gmail=...)                                       |
| `src/email_assistant/tools/common.py`                      | Question, Done                                                     |
| `src/email_assistant/tools/gmail/*.py`                     | send_email, fetch_emails, mark_as_read, calendar, prompt_templates |
| `src/email_assistant/db/store.py`                          | Store for memory                                                   |
| `src/email_assistant/db/checkpointer.py`                   | PostgresSaver wrapper                                              |
| `scripts/run_agent.py`                                     | Load .env, run simple agent, print last message                     |
| `langgraph.json`                                          | LangGraph Studio: graphs and env; `langgraph dev` uses this        |
| `migrations/`                                              | DB schema (SQL in Phase 3)                                         |
| `notebooks/`                                               | Notebook (Phase 7)                                                 |
| `tests/`                                                   | Tests                                                              |


