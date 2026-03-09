# Architecture

Flow, graph, state, and data flow.

## One agent with two subagents

The agent is a **single compiled graph** with two **subagents** (compiled subgraphs added as nodes):

1. **Email Assistant subagent** — triage (ignore / notify / respond) and HITL (`interrupt()` for notify). When it exits, the parent reads `classification_decision` and `_notify_choice` and routes to prepare_messages (respond) or END (ignore).
2. **Response subagent** — chat → tools → persist_messages (same tool loop as before). Handles both question mode and the respond path after triage. Reply context is injected by the **prepare_messages** node before this subgraph runs.

**Top-level flow:**

- `START → input_router` → if `email_input`: **email_assistant** (subgraph); else: **prepare_messages**.
- After **email_assistant**: if respond (direct or after notify resume) → **prepare_messages**; else END.
- **prepare_messages** → **response_agent** (subgraph) → **mark_as_read** → END.

**State:** `State` — `messages`, `email_input`, `classification_decision`, `email_id`, `_notify_choice`, `user_message`, `question`. Input schema: `StateInput`.

**Triage:** One LLM call with `RouterSchema`. When the graph is compiled with a **store** (Phase 6), triage loads `triage_preferences` from memory and injects them into the triage system prompt. On **notify**, `triage_interrupt_handler` calls `interrupt(...)`; subgraph exits to END; parent resumes with `Command(resume="respond")` or `Command(resume="ignore")`.

**prepare_messages:** If `email_id` and `email_input` are set, prepends a HumanMessage with reply context so the Response subgraph can call `send_email_tool(..., email_id=...)`. When `email_input._source == "gmail"`, the context states that the email just arrived in the user's Gmail inbox so the agent knows it is an incoming message.

**mark_as_read:** After the Response subgraph, when `email_id` is set, marks the Gmail message as read.

## Response subgraph (Subagent 2)

- **Graph:** `START → chat → tool_approval_gate` (when last message has tool_calls) or `persist_messages → END`. From `tool_approval_gate`: if approved → **tools** → chat; if declined → **chat**. Tools: send_email_tool, fetch_emails_tool, check_calendar_tool, schedule_meeting_tool, question_tool, done_tool.
- **Phase 6 HITL:** Before running **tools**, if any tool call is `send_email_tool` or `schedule_meeting_tool`, `tool_approval_gate` calls `interrupt(...)`; caller resumes with `Command(resume=True)` to run or `Command(resume=False)` to decline (agent receives "User declined" ToolMessages).
- **Phase 6 memory:** When the graph is compiled with a **store**, the chat node loads `response_preferences` and `cal_preferences` from the store and injects them into the system prompt via `get_agent_system_prompt_hitl_memory()`.
- **State:** Uses full `State` (including `_tool_approval`). Built by `simple_agent.build_response_subgraph(checkpointer, store)` (alias `build_simple_graph`).
