# Explanation: `simple_agent.py`

Detailed walkthrough of the **Response subgraph**: the chat → tools → persist loop used as a subagent in the main Email Assistant graph. Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–6)

```python
"""
Response subgraph: chat → tools → persist_messages. Used as subagent in the main agent.

Use cases: user can ask to send an email; agent uses send_email_tool and tool-call loop.
Persists messages to Supabase/Postgres when DATABASE_URL is set. Exposed as build_response_subgraph().
"""
```

- **Line 2:** This module defines the **Response subgraph**: a small graph that runs **chat** (LLM with tools), then optionally **tools** (tool execution), then **persist_messages**. It is used as a **subagent**—a single node—in the main agent (`email_assistant_hitl_memory_gmail.py`).
- **Lines 4–5:** Typical use: the user asks to send an email; the agent uses tools (e.g. `send_email_tool`) in a loop (chat → tools → chat …) until there are no more tool calls, then persists.
- **Line 5:** When **DATABASE_URL** is set, the subgraph persists **messages** to Supabase/Postgres (via `persist_messages`).
- **Line 6:** The public API is **build_response_subgraph()**, which returns the compiled subgraph.

---

## 2. Imports (lines 8–18)

```python
import os
```

- Used to read environment variables: **OPENAI_MODEL**, **OPENAI_API_KEY**, **DATABASE_URL**, **USER_ID**.

```python
from langchain_core.messages import AIMessage, SystemMessage
```

- **AIMessage:** Type of message from the assistant; we check whether it has **tool_calls** to decide if we need to run the tools node.
- **SystemMessage:** Wraps the system prompt sent to the LLM before the conversation messages.

```python
from langchain_openai import ChatOpenAI
```

- **ChatOpenAI:** LLM client used in **\_chat_node** to call the OpenAI API with the chosen model and optional tools.

```python
from langgraph.config import get_config
```

- **get_config():** Returns the current LangGraph **config** (e.g. from the run’s `configurable`). Used in **\_persist_messages_node** to read **thread_id** and **user_id** for persistence.

```python
from langgraph.graph import END, START, StateGraph
```

- **END, START:** Graph boundaries; START is the first node, END is where the subgraph finishes.
- **StateGraph:** Builder for the subgraph; same pattern as the main graph (add nodes/edges, then compile).

```python
from langgraph.prebuilt import ToolNode
```

- **ToolNode:** Prebuilt node that executes **tool calls** from the last message. Given a list of tools, it runs the matching tool for each call and returns tool result messages. We use it as the **"tools"** node.

```python
from email_assistant.prompts import get_agent_system_prompt_with_tools
from email_assistant.schemas import State
from email_assistant.tools import get_tools
```

- **get_agent_system_prompt_with_tools:** Returns the system prompt text that describes the agent’s role and available tools (see `prompts.py`).
- **State:** Shared state type (messages, email_input, etc.); the subgraph uses the same State as the rest of the app.
- **get_tools:** Returns the list of tools (e.g. send_email, Gmail helpers); we pass **include_gmail=True** so Gmail tools are included.

---

## 3. `_chat_node` (lines 21–36)

**Purpose:** Invoke the LLM with tools; return the assistant message (which may contain tool_calls). This is the main “chat” step in the tool loop.

```python
def _chat_node(state: State) -> dict:
    """
    Call LLM with tools; return the assistant message (may contain tool_calls).

    Use cases: first step in tool loop; when no tool_calls, next node is persist then END.
    """
```

- Takes the current **state**, returns a **dict** that is merged into state (here we only add **messages**).
- When the LLM doesn’t call tools, the next node is **persist_messages** then END; when it does call tools, the next node is **tools**, then we loop back to **chat**.

```python
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )
```

- **ChatOpenAI** is configured from env: **OPENAI_MODEL** (default **gpt-4o**), **OPENAI_API_KEY**. A new client is created on each call (no global singleton in this file).

```python
    tools = get_tools(include_gmail=True)
    llm_with_tools = llm.bind_tools(tools)
```

- **get_tools(include_gmail=True):** Loads the tool list including Gmail-related tools (see `email_assistant.tools`).
- **llm.bind_tools(tools):** Attaches the tools to the LLM so it can output **tool_calls** in the response when it wants to use a tool.

```python
    system = SystemMessage(content=get_agent_system_prompt_with_tools())
    messages = [system] + list(state["messages"])
```

- **system:** A single **SystemMessage** with the agent’s system prompt (role + tool descriptions).
- **messages:** The full list sent to the LLM: system first, then all existing **state["messages"]** (user and assistant messages, and any tool results from previous turns).

```python
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}
```

- **invoke(messages):** One LLM call; **response** is an **AIMessage** (possibly with **tool_calls**).
- **return {"messages": [response]}:** LangGraph merges this into state by **appending** the new message(s) to **state["messages"]**, so the next node sees the assistant message (and can check for tool_calls).

---

## 4. `_should_continue` (lines 39–47)

**Purpose:** After **chat**, decide the next node: **tools** (if the last message has tool_calls) or **persist_messages** (to finish the subgraph).

```python
def _should_continue(state: State) -> str:
    """Route to tools if last message has tool_calls, else to persist."""
```

- Used as the **conditional edge router** after the **"chat"** node. Return value must match a key in the routing map: **"tools"** or **"persist_messages"**.

```python
    messages = state.get("messages", [])
    if not messages:
        return "persist_messages"
```

- **messages:** Current conversation (including the message just added by _chat_node). If empty (shouldn’t happen after chat), we go straight to **persist_messages** to avoid errors.

```python
    last = messages[-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    return "persist_messages"
```

- **last:** The last message (the assistant response from _chat_node).
- **isinstance(last, AIMessage):** Ensures it’s an assistant message.
- **getattr(last, "tool_calls", None):** If the AIMessage has a **tool_calls** attribute and it’s truthy (non-empty list of tool calls), we need to run tools → return **"tools"**.
- Otherwise (no tool calls or not an AIMessage) → return **"persist_messages"** so the graph goes to persist then END.

---

## 5. `_persist_messages_node` (lines 50–73)

**Purpose:** When **DATABASE_URL** is set and there are messages, persist **state["messages"]** to the database (e.g. Supabase/Postgres). Uses **thread_id** and **user_id** from LangGraph config so messages are stored per thread/user.

```python
def _persist_messages_node(state: State) -> dict:
    """
    When DATABASE_URL is set, persist state["messages"] to email_assistant.messages.

    Use cases: run after chat so messages are stored when using CLI or LangSmith Studio.
    Reads thread_id and user_id from LangGraph config (get_config()).
    """
```

- Returns a **dict** merged into state; this node returns **{}** so it doesn’t change state, it only has a side effect (DB write).
- **thread_id** and **user_id** come from **get_config()** so the same thread/user as the run are used for persistence.

```python
    conn_string = os.getenv("DATABASE_URL")
    if not conn_string or not state.get("messages"):
        return {}
```

- **conn_string:** Database URL. If **DATABASE_URL** is not set, or there are no messages, we skip persistence and return **{}** (no state update).

```python
    try:
        config = get_config()
        configurable = config.get("configurable") or {}
        thread_id = configurable.get("thread_id", "default-thread")
        user_id = configurable.get("user_id", os.getenv("USER_ID", "default-user"))
    except Exception:
        thread_id = "default-thread"
        user_id = os.getenv("USER_ID", "default-user")
```

- **get_config():** LangGraph’s current config (e.g. passed when invoking the graph). **configurable** often holds **thread_id** and **user_id**.
- **thread_id:** From config, or **"default-thread"**.
- **user_id:** From config, or env **USER_ID**, or **"default-user"**.
- If **get_config()** or config access fails (e.g. no config in some contexts), we fall back to the same defaults so the node doesn’t crash.

```python
    try:
        from email_assistant.db.persist_messages import persist_messages
        persist_messages(conn_string, thread_id, user_id, list(state["messages"]))
    except Exception:
        pass  # Don't fail the graph if DB write fails
    return {}
```

- **persist_messages(...):** Writes the messages to the database (e.g. **email_assistant.messages** or similar table keyed by thread_id/user_id). See `email_assistant.db.persist_messages`.
- **list(state["messages"]):** Ensures we pass a list (state might be a tuple or other sequence).
- **except Exception: pass:** If the DB write fails (e.g. connection error, schema issue), we ignore it and don’t fail the graph—the run still completes; only persistence is skipped.
- **return {}:** No state update; this node is side-effect only.

---

## 6. `build_response_subgraph` (lines 76–95)

**Purpose:** Build and compile the Response subgraph: START → chat → (tools → chat)* → persist_messages → END. Optional checkpointer; when used as a node in the main graph, the main graph typically passes **checkpointer=None** so only the top-level graph has a checkpointer.

```python
def build_response_subgraph(checkpointer=None):
    """
    Build and compile the Response subgraph: START → chat → (tools → chat)* → persist_messages → END.

    Use cases: added as a node to the main agent; when DATABASE_URL is set, messages are persisted.
    """
```

- **checkpointer=None:** If provided, the compiled subgraph will use it (rare for this subgraph when used inside the main agent; the main agent usually compiles this with **None** and attaches a checkpointer only at the top level).
- Flow: always start at **chat**; then either **tools** (and loop back to **chat**) or **persist_messages** → END. The **(tools → chat)*** is the tool-call loop.

```python
    tools = get_tools(include_gmail=True)
    tool_node = ToolNode(tools)
```

- **tools:** Same tool list as in _chat_node (must match so tool names align).
- **ToolNode(tools):** LangGraph’s prebuilt node that, given the last message’s **tool_calls**, runs each tool and returns a list of **ToolMessage** results. Those get appended to state["messages"], and we then go back to **chat**.

```python
    builder = StateGraph(State)
    builder.add_node("chat", _chat_node)
    builder.add_node("tools", tool_node)
    builder.add_node("persist_messages", _persist_messages_node)
```

- **StateGraph(State):** Same state type as the rest of the app.
- **"chat":** _chat_node — LLM with tools.
- **"tools":** tool_node — executes tool calls.
- **"persist_messages":** _persist_messages_node — writes messages to DB when DATABASE_URL is set.

```python
    builder.add_edge(START, "chat")
```

- Subgraph always starts with **chat**.

```python
    builder.add_conditional_edges("chat", _should_continue, {"tools": "tools", "persist_messages": "persist_messages"})
```

- After **chat**, **\_should_continue(state)** is called. It returns **"tools"** or **"persist_messages"**. The map sends **"tools"** → **tools** node, **"persist_messages"** → **persist_messages** node.

```python
    builder.add_edge("tools", "chat")
```

- After **tools** runs, we go back to **chat** so the LLM can see the tool results and possibly issue more tool calls (tool loop).

```python
    builder.add_edge("persist_messages", END)
```

- After **persist_messages**, the subgraph ends (**END**). Control returns to the parent graph (e.g. to **mark_as_read** in the main agent).

```python
    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()
```

- If a checkpointer was passed, compile with it; otherwise compile without one. When this subgraph is used inside **build_email_assistant_graph**, it is called with **checkpointer=None** so the parent’s checkpointer is the single place for persistence and interrupts.

---

## 7. Backward compatibility alias (lines 97–98)

```python
# Backward compatibility for code that imports build_simple_graph.
build_simple_graph = build_response_subgraph
```

- **build_simple_graph** is an alias for **build_response_subgraph**. Code that still imports **build_simple_graph** (e.g. from an older version or another script) will get the same function without renaming imports.

---

## 8. Flow summary

1. **START** → **chat** (_chat_node: LLM with tools, appends one AIMessage).
2. **chat** → **\_should_continue**:  
   - If last message has **tool_calls** → **tools** (ToolNode runs tools, appends ToolMessages).  
   - Else → **persist_messages**.
3. **tools** → **chat** (loop until the LLM stops calling tools).
4. **persist_messages** → **END** (and optionally persist messages to DB).

So: one subgraph, three nodes (**chat**, **tools**, **persist_messages**), one router (**\_should_continue**), and a single tool loop implemented by the conditional edge plus **tools → chat** edge.

---

## 9. Related files

- **State:** `src/email_assistant/schemas.py`
- **Prompts:** `src/email_assistant/prompts.py` (`get_agent_system_prompt_with_tools`)
- **Tools:** `src/email_assistant/tools/` (`get_tools`)
- **Persistence:** `src/email_assistant/db/persist_messages.py` (`persist_messages`)
- **Usage:** `src/email_assistant/email_assistant_hitl_memory_gmail.py` (adds this subgraph as the **response_agent** node)

For the top-level flow and where this subgraph fits, see **docs/code-explanations/email_assistant_hitl_memory_gmail.md**.
