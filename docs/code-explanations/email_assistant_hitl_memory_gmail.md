# Explanation: `email_assistant_hitl_memory_gmail.py`

Detailed walkthrough of the **entry point** that builds and compiles the top-level Email Assistant graph. Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–7)

```python
"""
Entry: build and compile the top-level graph with two subagents (Email Assistant, Response).

Use cases: one agent (START → input_router → email_assistant subgraph or prepare_messages → response_agent subgraph → mark_as_read).
For LangGraph Studio the graph is exported without a checkpointer (API provides one). For CLI (run_agent.py)
pass an explicit checkpointer (MemorySaver or Postgres) for HITL and thread persistence.
"""
```

- **Line 2:** This file is the **entry**: it builds and compiles the single top-level graph that contains two subagents (Email Assistant and Response).
- **Lines 4–5:** Describes the flow: from START you always hit **input_router**; then either the **email_assistant** subgraph (triage path) or **prepare_messages**; after that, **response_agent** subgraph and **mark_as_read**.
- **Lines 5–6:** **LangGraph Studio** uses the graph without passing a checkpointer in code—the API/server provides one. For the **CLI** (e.g. `run_agent.py`), you must pass an explicit checkpointer (e.g. `MemorySaver` or Postgres) so that HITL (human-in-the-loop) and thread persistence work.

---

## 2. Imports (lines 9–17)

```python
from langgraph.graph import END, START, StateGraph
```

- **END:** Constant meaning “end of the graph”; used as the target of edges that finish the graph or a subgraph.
- **START:** Constant meaning “graph start”; used as the source of the first edge(s).
- **StateGraph:** Class to build a state graph: add nodes and edges, then `.compile()` to get a runnable graph.

```python
from email_assistant.schemas import State, StateInput
```

- **State:** Typed state shared by the whole graph (e.g. `messages`, `email_input`, `classification_decision`, `_notify_choice`, `email_id`). Every node reads/writes this state.
- **StateInput:** Schema for **input** to the graph (what callers can pass when invoking it); used as `input_schema` for the top-level builder.

```python
from email_assistant.nodes.input_router import input_router
from email_assistant.nodes.triage import triage_router
from email_assistant.nodes.triage_interrupt import triage_interrupt_handler
from email_assistant.nodes.prepare_messages import prepare_messages
from email_assistant.nodes.mark_as_read import mark_as_read_node
```

- **input_router:** First node; normalizes input and sets things like `email_input` so the graph can route “email mode” vs “question mode.”
- **triage_router:** Node that classifies the current email (ignore / notify / respond) and sets `classification_decision`.
- **triage_interrupt_handler:** Node run when classification is **notify**; it calls `interrupt()` so the user can choose respond or ignore and sets `_notify_choice`.
- **prepare_messages:** Node that, when replying to an email, injects reply context into `messages`, then hands off to the response subgraph.
- **mark_as_read_node:** Node that marks the Gmail message as read when `email_id` is present.

```python
from email_assistant.simple_agent import build_response_subgraph
```

- **build_response_subgraph:** Function that builds and returns a **compiled subgraph** (chat node, tools, persist_messages). That compiled graph is added as a single node named `response_agent` in the top-level graph.

---

## 3. `_after_triage_route` (lines 19–24)

**Purpose:** Inside the Email Assistant subgraph, decide what happens after **triage_router**: go to the notify handler or end the subgraph.

```python
def _after_triage_route(state: State) -> str:
```

- Function used as a **conditional edge router**. It receives the current **state** and returns a **string** that matches a key in the routing map (see `add_conditional_edges` below).

```python
    """Inside Email Assistant subgraph: ignore/respond → END, notify → triage_interrupt_handler."""
```

- Docstring: if the decision is **ignore** or **respond**, the subgraph goes to END; if **notify**, the next node is **triage_interrupt_handler**.

```python
    decision = (state.get("classification_decision") or "").strip().lower()
```

- **state.get("classification_decision")** — Value set by `triage_router` (e.g. `"ignore"`, `"notify"`, `"respond"`).
- **or ""** — If the key is missing or None, use an empty string so we don’t call `.strip()` on None.
- **.strip().lower()** — Normalize whitespace and case so we can compare with `"notify"` reliably.

```python
    if decision == "notify":
        return "triage_interrupt_handler"
    return "__end__"
```

- If the decision is **notify**, return the string **"triage_interrupt_handler"** so the graph goes to that node (which will interrupt for the user).
- In all other cases (ignore, respond, or empty), return **"__end__"** so the subgraph goes to **END**. The parent graph then uses the same state (including `classification_decision` and, after notify, `_notify_choice`) to route to prepare_messages or END.

---

## 4. `build_email_assistant_subgraph` (lines 27–42)

**Purpose:** Build the Email Assistant subgraph: triage → optional notify handler → end. No checkpointer here; the parent’s checkpointer is used for interrupts.

```python
def build_email_assistant_subgraph():
    """
    Build the Email Assistant subgraph: triage_router → ignore/respond → END, notify → triage_interrupt_handler → END.

    No checkpointer (parent's checkpointer handles interrupt). Parent reads state after this subgraph exits and routes to prepare_messages or END.
    """
```

- The subgraph always starts with **triage_router**. Then: **ignore/respond** → END; **notify** → **triage_interrupt_handler** → END. The parent graph’s checkpointer is used when the handler calls `interrupt()`.

```python
    builder = StateGraph(State)
```

- Creates a **StateGraph** whose state type is **State**. All nodes in this subgraph read/write the same State as the rest of the app.

```python
    builder.add_node("triage_router", triage_router)
    builder.add_node("triage_interrupt_handler", triage_interrupt_handler)
```

- **"triage_router"** — Node that runs the triage LLM and sets `classification_decision`.
- **"triage_interrupt_handler"** — Node that runs only when classification is notify; it interrupts and sets `_notify_choice`.

```python
    builder.add_edge(START, "triage_router")
```

- The subgraph’s first step is always **triage_router**.

```python
    builder.add_conditional_edges("triage_router", _after_triage_route, {
        "triage_interrupt_handler": "triage_interrupt_handler",
        "__end__": END,
    })
```

- **"triage_router"** is the source node.
- **\_after_triage_route** is the router function: it returns either `"triage_interrupt_handler"` or `"__end__"`.
- **Map:** If the return value is `"triage_interrupt_handler"`, the next node is **triage_interrupt_handler**; if `"__end__"`, the graph goes to **END** (subgraph ends).

```python
    builder.add_edge("triage_interrupt_handler", END)
```

- After the handler runs (and the user resumes), the subgraph goes to **END**. State (including `_notify_choice`) is then used by the parent’s conditional edges.

```python
    return builder.compile()
```

- Compiles the subgraph and returns it. This compiled graph is later added as a **single node** (`email_assistant`) in the top-level graph. No checkpointer is passed—the parent graph’s checkpointer is used.

---

## 5. `_after_input_router_route` (lines 45–50)

**Purpose:** Right after **input_router**, decide whether to run the email_assistant subgraph or go straight to prepare_messages (question path).

```python
def _after_input_router_route(state: State) -> str:
    """Route from input_router: email path → email_assistant subgraph, question path → prepare_messages."""
```

- Router used by the **top-level** graph’s conditional edges after **input_router**. Email path = **email_assistant**; question path = **prepare_messages**.

```python
    if state.get("email_input"):
        return "email_assistant"
    return "prepare_messages"
```

- **state.get("email_input")** — Set by **input_router** when the user is in “email mode” (e.g. replying to or triaging an email). If truthy, we go to the **email_assistant** subgraph (triage).
- Otherwise we go to **prepare_messages**, which then feeds into **response_agent** with no triage.

---

## 6. `_after_email_assistant_route` (lines 52–58)

**Purpose:** After the **email_assistant** subgraph has finished, decide whether to run the response agent (prepare_messages) or end the graph.

```python
def _after_email_assistant_route(state: State) -> str:
    """After Email Assistant subgraph: respond → prepare_messages, else END."""
```

- Router used by the top-level graph’s conditional edges after the **email_assistant** node (subgraph) exits. “Respond” (from triage or from notify HITL) → **prepare_messages**; else → END.

```python
    if (state.get("classification_decision") or "").strip().lower() == "respond":
        return "prepare_messages"
```

- **classification_decision** is set by **triage_router**. If it is **"respond"**, we should reply → go to **prepare_messages** (which then runs the response_agent subgraph).

```python
    if (state.get("_notify_choice") or "").strip().lower() == "respond":
        return "prepare_messages"
```

- **\_notify_choice** is set by **triage_interrupt_handler** when the user was shown a “notify” email and chose “respond.” Same outcome: go to **prepare_messages**.

```python
    return "__end__"
```

- If we didn’t return above (ignore, or notify and user chose ignore), the graph goes to **END** and does not run the response agent or mark_as_read.

---

## 7. `build_email_assistant_graph` (lines 61–97)

**Purpose:** Build and compile the **top-level** graph: input_router → email_assistant or prepare_messages → prepare_messages → response_agent → mark_as_read → END, with optional checkpointer.

```python
def build_email_assistant_graph(checkpointer=None):
    """
    Build and compile the one agent with two subagents.

    Flow: START → input_router → (email_input ? email_assistant subgraph : prepare_messages)
    - email_assistant subgraph → (respond ? prepare_messages : END)
    - prepare_messages → response_agent subgraph → mark_as_read → END
    """
```

- **checkpointer=None** — Optional. If provided (e.g. by CLI), the compiled graph will use it for persistence and HITL. If None (e.g. for Studio), the API injects the checkpointer.
- Docstring summarizes: one agent, two subgraphs; the branching at input_router and after email_assistant; then the linear tail prepare_messages → response_agent → mark_as_read → END.

```python
    email_subgraph = build_email_assistant_subgraph()
```

- Builds the Email Assistant subgraph (triage_router + conditional → triage_interrupt_handler or END). This is the “email triage” part of the flow.

```python
    response_subgraph = build_response_subgraph(checkpointer=None)
```

- Builds the Response subgraph (chat, tools, persist_messages). It is **always** compiled with **checkpointer=None** so that only the **top-level** graph has a checkpointer; that way interrupt/resume and thread state are managed in one place.

```python
    builder = StateGraph(State, input_schema=StateInput)
```

- **State** — Type of the graph state for all nodes.
- **input_schema=StateInput** — Declares the allowed **input** shape when the graph is invoked (e.g. from Studio or CLI).

```python
    builder.add_node("input_router", input_router)
    builder.add_node("email_assistant", email_subgraph)
    builder.add_node("prepare_messages", prepare_messages)
    builder.add_node("response_agent", response_subgraph)
    builder.add_node("mark_as_read", mark_as_read_node)
```

- **"input_router"** — The input_router function (first node).
- **"email_assistant"** — The compiled Email Assistant subgraph as a single node.
- **"prepare_messages"** — The prepare_messages function.
- **"response_agent"** — The compiled Response subgraph as a single node.
- **"mark_as_read"** — The mark_as_read_node function.

```python
    builder.add_edge(START, "input_router")
```

- The graph always starts at **input_router**.

```python
    builder.add_conditional_edges("input_router", _after_input_router_route, {
        "email_assistant": "email_assistant",
        "prepare_messages": "prepare_messages",
    })
```

- After **input_router**, **\_after_input_router_route(state)** is called. It returns either **"email_assistant"** or **"prepare_messages"**. The map sends each return value to the node with that name.

```python
    builder.add_conditional_edges("email_assistant", _after_email_assistant_route, {
        "prepare_messages": "prepare_messages",
        "__end__": END,
    })
```

- After the **email_assistant** subgraph exits, **\_after_email_assistant_route(state)** is called. It returns **"prepare_messages"** (to run the response agent) or **"__end__"** (to go to END). The map connects those to the **prepare_messages** node or **END**.

```python
    builder.add_edge("prepare_messages", "response_agent")
```

- After **prepare_messages**, control always goes to the **response_agent** subgraph (which may run multiple steps internally).

```python
    builder.add_edge("response_agent", "mark_as_read")
```

- When the **response_agent** subgraph finishes, control goes to **mark_as_read**.

```python
    builder.add_edge("mark_as_read", END)
```

- After **mark_as_read**, the graph reaches **END**.

```python
    # When run under LangGraph API (Studio), do not pass a checkpointer; the API provides one.
    # For CLI (run_agent.py), pass an explicit checkpointer (e.g. MemorySaver()) for HITL/threads.
    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()
```

- **If checkpointer is not None** (e.g. CLI): compile with that checkpointer so state and interrupts are persisted.
- **Otherwise** (e.g. Studio): compile with no checkpointer; the LangGraph server will attach the checkpointer from config (e.g. `langgraph.json`).

---

## 8. Exported graph (lines 99–100)

```python
# For LangGraph Studio: export graph without checkpointer so the API can load it.
email_assistant = build_email_assistant_graph()
```

- **Comment:** The Studio dev server loads this graph; it expects no checkpointer in code and injects one from configuration.
- **email_assistant:** A **compiled** graph instance built with **no** checkpointer. Used when the app is run via the LangGraph API (e.g. `langgraph.json` pointing at this module and the `email_assistant` symbol). The server then adds the checkpointer (e.g. from `studio_checkpointer`) for Studio’s persistence and resume.

CLI scripts (**run_agent.py**, **watch_gmail.py**) typically do **not** use this global; they call **build_email_assistant_graph(checkpointer=...)** and pass their own checkpointer (e.g. MemorySaver or Postgres).

---

## 9. Flow summary

1. **START** → **input_router**
2. **input_router** → **\_after_input_router_route**:  
   - if `email_input` → **email_assistant** (subgraph: triage_router → triage_interrupt_handler or END)  
   - else → **prepare_messages**
3. **email_assistant** (when used) → **\_after_email_assistant_route**:  
   - if respond or _notify_choice == respond → **prepare_messages**  
   - else → **END**
4. **prepare_messages** → **response_agent** (subgraph) → **mark_as_read** → **END**

So: one top-level graph, two subgraphs as nodes (**email_assistant**, **response_agent**), and three router functions (**\_after_triage_route**, **\_after_input_router_route**, **\_after_email_assistant_route**) that implement the branching.

---

## 10. Related files

- **State / StateInput:** `src/email_assistant/schemas.py`
- **Nodes:** `src/email_assistant/nodes/` (input_router, triage, triage_interrupt, prepare_messages, mark_as_read)
- **Response subgraph:** `src/email_assistant/simple_agent.py` (`build_response_subgraph`)
- **Studio config:** `langgraph.json` (graph and checkpointer path)

For architecture and high-level flow, see **docs/guide/03_ARCHITECTURE_AND_FLOW.md**.
