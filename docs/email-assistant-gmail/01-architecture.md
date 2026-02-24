# Architecture: Graph, State, and Flow

## Graph Structure

The agent is a **two-level** LangGraph workflow:

1. **Top-level workflow**  
   - Single entry: `START → triage_router`.  
   - From the router, control goes to either `response_agent`, `triage_interrupt_handler`, or `END`.

2. **Response agent** (subgraph)  
   - Entry: `START → llm_call`.  
   - After each `llm_call`, a conditional edge routes to either `interrupt_handler` or `mark_as_read_node`; `mark_as_read_node` then goes to `END`.

So the **overall** flow is:

- **START** → **triage_router**
  - **respond** → **response_agent** (subgraph) → eventually **mark_as_read_node** → **END**
  - **ignore** → **END**
  - **notify** → **triage_interrupt_handler** → either **response_agent** or **END**

Inside the response agent:

- **START** → **llm_call** → (if tool calls and no Done) **interrupt_handler** → **llm_call** (loop)  
- **llm_call** → (if Done) **mark_as_read_node** → **END**

### Node Roles

| Node | Type | Role |
|------|------|------|
| `triage_router` | Command node | Parses email, loads triage memory, runs router LLM, returns `Command(goto=..., update=...)` to `response_agent`, `triage_interrupt_handler`, or `END`. |
| `triage_interrupt_handler` | Command node | Handles **notify**: shows email in Agent Inbox via `interrupt()`, then either goes to `response_agent` (user chose to respond) or `END` (user ignored). Updates triage memory from the choice. |
| `response_agent` | Compiled subgraph | Runs the loop: `llm_call` → conditional → `interrupt_handler` or `mark_as_read_node`. |
| `llm_call` | State-update node | Loads cal/response memory, runs the agent LLM with tools; returns updated `messages`. |
| `interrupt_handler` | Command node | For each tool call in the last message: HITL tools go to Agent Inbox; others run directly. Returns `Command(goto=llm_call|END, update={messages}). |
| `mark_as_read_node` | State-update node | Calls Gmail `mark_as_read(email_id)` when `email_id` is present. |

The top-level graph also registers `mark_as_read_node` so the **respond** path can run it after the response agent finishes (see code: response agent ends at `mark_as_read_node` → END; the top-level graph wires that same node to END).

## State

State is **`State`**, which extends **`MessagesState`** and adds:

- **`email_input`** (`dict`): Raw email payload (Gmail format or mock/Studio format). Consumed by triage and response agent (e.g. for `parse_gmail`, `format_gmail_markdown`).
- **`classification_decision`** (`Literal["ignore", "respond", "notify"]`): Set by `triage_router` and used by `triage_interrupt_handler` in the interrupt request.

`MessagesState` provides **`messages`**: the conversation history (user, assistant, tool messages) used by the response agent.

All transitions use **`Command(goto=..., update=...)`** where applicable so that state updates and routing are explicit.

## Data Flow Summary

1. **Input**: `StateInput` with `email_input` (and optionally a checkpointer/thread config for memory).
2. **Triage**: `triage_router` parses `email_input` with `parse_gmail`, builds triage prompt with `get_memory(..., "triage_preferences", ...)`, invokes `llm_router` with `RouterSchema`, then returns a `Command` to one of: `response_agent`, `triage_interrupt_handler`, or `END`.
3. **Notify path**: `triage_interrupt_handler` creates an interrupt with the email markdown; on "response" it appends user feedback to `messages` and updates triage memory, then goes to `response_agent`; on "ignore" it updates triage memory and goes to `END`.
4. **Respond path**: `response_agent` runs with initial `messages` (e.g. "Respond to the email: …"). Each `llm_call` may produce tool calls; `interrupt_handler` runs or interrupts per tool; results are appended to `messages` and the loop continues until the model calls **Done**, then `mark_as_read_node` runs and the graph ends.
5. **Memory**: Read via `get_memory(store, namespace, default_*)` and written via `update_memory(store, namespace, messages)` in triage and interrupt handlers (namespaces: `("email_assistant", "triage_preferences")`, `("email_assistant", "response_preferences")`, `("email_assistant", "cal_preferences")`).

## File Reference

- **Entry point**: `src/email_assistant/email_assistant_hitl_memory_gmail.py`
- **State/schemas**: `src/email_assistant/schemas.py` (`State`, `StateInput`, `RouterSchema`, `UserPreferences`)
- **Graph**: Built with `StateGraph(State)`, `add_node`, `add_edge`, `add_conditional_edges`, and `compile()`; top-level graph compiles to **`email_assistant`**.
