# Code explanations

File-by-file walkthrough of the codebase. Each markdown file explains one (or a related set of) source file in detail.

**Start here:** [email_assistant_hitl_memory_gmail.md](email_assistant_hitl_memory_gmail.md) — the entry point that builds and compiles the top-level graph.

| File | Explanation |
|------|--------------|
| [email_assistant_hitl_memory_gmail.md](email_assistant_hitl_memory_gmail.md) | Entry point: graph build, subgraphs, routing, checkpointer. |
| [simple_agent.md](simple_agent.md) | Response subgraph: chat node, tools loop, persist_messages, build_response_subgraph. |
| [schemas.md](schemas.md) | State, StateInput, MessagesState, ClassificationDecision, RouterSchema, NotifyChoiceSchema. |
| [prompts.md](prompts.md) | Triage, agent, and notify-choice prompts; get_triage_*, get_agent_system_prompt_*, constants. |
| [nodes_input_router.md](nodes_input_router.md) | input_router node: normalize input, email_input vs question path, _normalize_email_input. |
| [nodes_triage.md](nodes_triage.md) | triage_router node: classify ignore/notify/respond, RouterSchema, _is_explicit_request. |
| [nodes_triage_interrupt.md](nodes_triage_interrupt.md) | triage_interrupt_handler: interrupt() for notify HITL, _notify_choice, NOTIFY_INTERRUPT_MESSAGE. |
| [nodes_prepare_messages.md](nodes_prepare_messages.md) | prepare_messages: inject reply context (email_id, from/subject/body) before Response subgraph. |
| [nodes_mark_as_read.md](nodes_mark_as_read.md) | mark_as_read_node: call Gmail mark_as_read when email_id set; no-op otherwise. |
| [tools_init.md](tools_init.md) | tools/__init__.py: get_tools(include_gmail), send_email_tool, question_tool, done_tool. |
| [tools_common.md](tools_common.md) | tools/common.py: question_tool, done_tool (@tool, docstrings, return values). |
| [tools_gmail_auth.md](tools_gmail_auth.md) | tools/gmail/auth.py: SCOPES, get_credentials (token/refresh/flow), get_gmail_service. |
| [tools_gmail_send_email.md](tools_gmail_send_email.md) | tools/gmail/send_email.py: send_email_tool, send_new_email, send_reply_email. |
| [tools_gmail_mark_as_read.md](tools_gmail_mark_as_read.md) | tools/gmail/mark_as_read.py: mark_as_read (Gmail modify, removeLabelIds UNREAD). |
| [tools_gmail_fetch_emails.md](tools_gmail_fetch_emails.md) | tools/gmail/fetch_emails.py: list_inbox_message_ids, get_message_as_email_input, fetch_recent_inbox. |
| [tools_gmail_prompt_templates.md](tools_gmail_prompt_templates.md) | tools/gmail/prompt_templates.py: get_gmail_tools_prompt, GMAIL_TOOLS_PROMPT (Tools section for agent). |
| [db_checkpointer.md](db_checkpointer.md) | db/checkpointer.py: postgres_checkpointer, run_checkpoint_created_at_migration, get_checkpointer. |
| [db_studio_checkpointer.md](db_studio_checkpointer.md) | db/studio_checkpointer.py: generate_checkpointer (async, AsyncPostgresSaver, setup()). |
| [db_store.md](db_store.md) | db/store.py: postgres_store (PostgresStore), setup_store (create store table). |
| [db_persist_messages.md](db_persist_messages.md) | db/persist_messages.py: persist_messages (users/chats/messages sync), thread_id_to_chat_id. |
| [fixtures_mock_emails.md](fixtures_mock_emails.md) | fixtures/mock_emails.py: MOCK_EMAIL_NOTIFY/RESPOND/IGNORE, get_mock_email (testing/HITL demos). |
| [scripts.md](scripts.md) | scripts/: run_agent, run_mock_email, setup_db, watch_gmail, debug_triage, simulate_gmail_email, test_gmail_read. |
| [config.md](config.md) | Config: .env.example (OpenAI, Gmail, DATABASE_URL, USER_ID), langgraph.json (graphs, checkpointer, env). |
| [migrations.md](migrations.md) | migrations/: 000 drop schema, 001 email_assistant tables (users, chats, messages, agent_memory), 002 checkpoint created_at. |
