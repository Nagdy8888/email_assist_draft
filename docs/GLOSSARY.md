# Glossary

Key terms used in the email assistant project.

- **chat_id** — Application-level conversation identifier; often aligned with LangGraph `thread_id` when storing messages in the `chats` table.

- **checkpointer** — LangGraph component that persists graph state (e.g. after each node). Enables multi-turn conversations and **interrupt**/resume. We use `PostgresSaver` (or `MemorySaver` for development) with `thread_id` in config.

- **classification_decision** — Output of the triage router: one of **ignore**, **notify**, **respond**. Drives conditional edges (e.g. notify → triage_interrupt_handler).

- **email_input** — Normalized email payload (from, to, subject, body, id) passed into the graph for **email mode**. Produced by input_router from raw Gmail API payload or from mock/flat dict.

- **email mode** — Flow where the graph receives an **email_input**; **input_router** sends to the Email Assistant subgraph (triage → ignore/notify/respond) instead of the question path.

- **HITL (human-in-the-loop)** — Points where the graph pauses and waits for a human decision. Implemented with `interrupt()` from `langgraph.types`; the caller resumes with `Command(resume=...)`. Used for: (1) **notify** (respond vs ignore), (2) send_email/schedule_meeting approval before running the tool.

- **ignore** — Triage outcome: no action; low value or noise. Graph ends without reply.

- **memory** — User preferences stored in the LangGraph **store** (e.g. triage_preferences, response_preferences, cal_preferences). Per user (not per chat). Injected into triage and response agent prompts via **get_memory** / **update_memory**.

- **namespaces** — Store keys for preferences: `triage_preferences`, `response_preferences`, `cal_preferences`. Each holds a single text profile per user.

- **notify** — Triage outcome: user should see the email but no reply required. Graph pauses at **triage_interrupt_handler**; user chooses **respond** or **ignore**.

- **question mode** — Flow where the graph receives a **user_message** or **question**; **input_router** sends to prepare_messages → response_agent (no triage).

- **respond** — Triage outcome: needs a direct reply or action. Graph goes to prepare_messages → response_agent (with email context and email_id for reply).

- **store** — LangGraph key-value store (e.g. **PostgresStore**) used for **memory** (user preferences). Passed as `compile(store=...)`. Nodes that need preferences receive the store (e.g. via closure) and call **get_memory** / **update_memory**.

- **thread_id** — LangGraph config key; identifies the conversation for the checkpointer. Same thread_id across invokes gives multi-turn and correct resume after **interrupt**.

- **triage** — Classification of an incoming email into ignore / notify / respond using the triage router (LLM + RouterSchema).

- **user_id** — User identifier in config; used for **memory** scoping (preferences are per user).
