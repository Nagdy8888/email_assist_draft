# Response Agent and Tools

This document covers the **response agent** subgraph: the **LLM node**, the **interrupt handler** (HITL), **tools**, and the **mark-as-read** step.

---

## 1. Response Agent Subgraph

The response agent is a compiled `StateGraph(State)` with:

- **Nodes**: `llm_call`, `interrupt_handler`, `mark_as_read_node`.
- **Edges**:  
  - `START → llm_call`  
  - `llm_call` → conditional **should_continue** → `interrupt_handler` or `mark_as_read_node`  
  - `mark_as_read_node → END`

So the loop is: **llm_call → (tool calls?) → interrupt_handler → (update messages) → llm_call** until the model calls **Done**, then **mark_as_read_node → END**.

---

## 2. LLM Node (`llm_call`)

### Role

Run the agent LLM with **required** tool use; inject triage result and memory into the system prompt.

### Steps

1. **Load memory**  
   - `cal_preferences = get_memory(store, ("email_assistant", "cal_preferences"), default_cal_preferences)`  
   - `response_preferences = get_memory(store, ("email_assistant", "response_preferences"), default_response_preferences)`

2. **Build system message**  
   `agent_system_prompt_hitl_memory.format(tools_prompt=GMAIL_TOOLS_PROMPT, background=default_background, response_preferences=..., cal_preferences=...)`

3. **Invoke**  
   `llm_with_tools.invoke([system] + state["messages"])` where `llm_with_tools = llm.bind_tools(tools, tool_choice="required")`.

4. **Return**  
   `{"messages": [assistant_message]}` (single new message appended to conversation).

The **tools** used are: `send_email_tool`, `schedule_meeting_tool`, `check_calendar_tool`, `Question`, `Done` (and any others passed to `get_tools(..., include_gmail=True)`). The prompt text is **GMAIL_TOOLS_PROMPT** (fetch_emails, send_email, check_calendar, schedule_meeting, triage_email, Done).

---

## 3. Conditional Edge: `should_continue`

- **Input**: `state["messages"]`, last message.
- **Logic**:  
  - If the last message has **tool_calls** and **any** of them is **Done** → return `"mark_as_read_node"`.  
  - If the last message has other tool calls → return `"interrupt_handler"`.  
  - (If no tool calls, the graph would still need to handle that; in practice the agent is instructed to always call a tool.)

So: **Done** exits the loop and runs mark-as-read; any other tool calls go to the interrupt handler.

---

## 4. Interrupt Handler (HITL)

### Role

For each tool call in the **last** assistant message:

- **HITL tools** (`send_email_tool`, `schedule_meeting_tool`, `Question`): send an **interrupt** to the Agent Inbox; then handle **accept** / **edit** / **ignore** / **response** and optionally update memory.
- **Non-HITL tools** (e.g. `check_calendar_tool`): run immediately and append a tool message; no interrupt.

The handler builds a list of follow-up messages (tool results and/or updated AI message with edited tool_calls) and returns `Command(goto="llm_call" | END, update={messages})`. If the user **ignores** a HITL action, `goto=END` so the workflow ends without further LLM steps.

### Interrupt Request Shape

For each HITL tool call:

- **action_request**: `{ "action": tool_name, "args": tool_call["args"] }`.
- **config**: Depends on tool (e.g. send_email_tool and schedule_meeting_tool allow ignore, respond, edit, accept; Question allows ignore, respond only).
- **description**: Original email markdown (from `state["email_input"]` via `parse_gmail` + `format_gmail_markdown`) plus `format_for_display(tool_call)`.

### Response Handling

- **accept**: Run the tool with original args, append tool message; keep `goto="llm_call"`.
- **edit**:  
  - Replace that tool call’s args in the last AI message with `response["args"]["args"]`, append the updated AI message and run the tool with **edited** args, append tool message.  
  - For **send_email_tool** / **schedule_meeting_tool**, call `update_memory` (response_preferences or cal_preferences) with the initial vs edited content and reinforcement instructions.
- **ignore**:  
  - Do **not** run the tool; append a tool message that tells the agent to “ignore this … and end the workflow.”  
  - Set `goto=END`.  
  - Update **triage_preferences** so similar emails are not classified as respond in the future.
- **response**:  
  - Do not run the tool; append a tool message with the user’s feedback for the model to incorporate.  
  - For send_email_tool / schedule_meeting_tool, call `update_memory` (response_preferences or cal_preferences).  
  - Keep `goto="llm_call"`.

Edited tool_calls are applied in an immutable way: copy the last message and replace its `tool_calls` with a list that has the edited call in place of the original.

---

## 5. Tools Used in This Agent

| Tool | HITL? | Purpose |
|------|-------|--------|
| **send_email_tool** | Yes | Send reply (or new email) via Gmail; args include email_id, response_text, email_address, optional additional_recipients. |
| **schedule_meeting_tool** | Yes | Create Google Calendar event and send invites; args: attendees, title, start_time, end_time, organizer_email, timezone. |
| **check_calendar_tool** | No | Check Google Calendar for given dates (list of DD-MM-YYYY); returns events and availability. |
| **Question** | Yes | Ask the user a question when the agent lacks context; user can answer (response) or ignore. |
| **Done** | No (special) | Signals task complete; triggers `mark_as_read_node` and exit. |

`fetch_emails_tool` is in GMAIL_TOOLS_PROMPT but not in the tool list passed to this agent (the list is `["send_email_tool", "schedule_meeting_tool", "check_calendar_tool", "Question", "Done"]`). So in this graph, emails are assumed to be supplied via `email_input` (e.g. from an ingest that uses `fetch_emails_tool` elsewhere).

---

## 6. Mark-as-Read Node (`mark_as_read_node`)

- **Input**: `state["email_input"]`.
- **Logic**: `author, to, subject, email_thread, email_id = parse_gmail(email_input)`; if `email_id` is present, call **`mark_as_read(email_id)`** (Gmail API: remove `UNREAD` label).
- **Purpose**: After the agent has finished (Done), mark the processed email as read so it doesn’t reappear in future fetches.

The same node is used both inside the response agent (after Done) and at the top level; the compiled graph wires it so that when the response agent exits via `mark_as_read_node`, that single node runs and then the workflow ends.
