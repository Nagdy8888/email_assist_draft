# Architecture

Flow, graph, state, and data flow.

# Architecture

Flow, graph, state, and data flow.

## Phase 4: Simple agent with tools (current)

- **Graph:** `START → chat → (tools → chat)* → persist_messages → END`. The **chat** node calls ChatOpenAI with `bind_tools(send_email_tool, question_tool, done_tool)`. If the assistant message has `tool_calls`, the **tools** node runs them (via LangGraph `ToolNode`) and appends `ToolMessage`s; then control returns to **chat**. When there are no tool_calls, control goes to **persist_messages** then END.
- **State:** `MessagesState` — `messages` with `add_messages` reducer.
- **Checkpointer:** Postgres when `DATABASE_URL` is set; else in-memory. Same thread_id gives multi-turn.
- **Tools:** `send_email_tool` (new email only; reply by email_id in Phase 5), `question_tool`, `done_tool`. Gmail OAuth via `.secrets/credentials.json` and `.secrets/token.json`.
- **Persistence:** When `DATABASE_URL` is set, **persist_messages** node writes to `email_assistant.messages` (CLI and LangGraph Studio).

Full graph (input_router, triage, response_agent subgraph, mark_as_read) is Phase 5.
