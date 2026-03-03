# Explanation: `schemas.py`

Detailed walkthrough of the **state and input schemas** used by the Email Assistant graph. Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–6)

```python
"""
State, StateInput, RouterSchema, and UserPreferences for the email assistant graph.

Use cases: define graph state (messages, email_input, classification_decision),
input types for email vs question mode, and structured outputs for triage and memory.
"""
```

- **Line 2:** This module defines the main types used by the graph: **State** (full graph state), **StateInput** (allowed input when invoking the graph), **RouterSchema** (triage LLM output), and related types. (Note: **UserPreferences** is mentioned in the docstring but not defined in this file; it may exist elsewhere or be planned.)
- **Lines 4–5:** **State** holds conversation **messages**, **email_input** (email payload in email mode), **classification_decision** (triage result), and other fields. **StateInput** describes what callers can pass for **email mode** (e.g. `email_input`) vs **question mode** (e.g. `user_message` / `question`). **RouterSchema** and **NotifyChoiceSchema** are used for **structured outputs** from the triage LLM and for the notify choice.

---

## 2. Imports (lines 8–11)

```python
from typing import Annotated, Literal, Optional
```

- **Annotated:** Used to attach metadata to a type (e.g. **add_messages** reducer for the **messages** field so LangGraph knows how to merge new messages into state).
- **Literal:** Restricts a value to specific strings (e.g. `"ignore" | "notify" | "respond"` for **ClassificationDecision**, `"respond" | "ignore"` for **NotifyChoiceSchema**).
- **Optional:** Shorthand for `T | None`; fields that may be absent or unset use **Optional[...]**.

```python
from typing_extensions import TypedDict
```

- **TypedDict:** Defines a dict with fixed keys and value types. Used for **State**, **StateInput**, **RouterSchema**, **NotifyChoiceSchema**, and **MessagesState**. From **typing_extensions** for compatibility with older Python; in Python 3.11+ you can use **typing.TypedDict**.

```python
from langgraph.graph.message import add_messages
```

- **add_messages:** LangGraph’s **reducer** for the **messages** field. When a node returns `{"messages": [new_message]}`, LangGraph doesn’t replace the list—it **appends** the new messages to the existing list (and can handle deduplication). So **messages** is an append-only conversation history.

---

## 3. `MessagesState` (lines 13–17)

```python
# Phase 2: minimal state for simple agent (messages only).
MessagesState = TypedDict(
    "MessagesState",
    {"messages": Annotated[list, add_messages]},
)
```

- **Comment:** From the phased plan, Phase 2 introduced a minimal state with only **messages** for the simple agent.
- **TypedDict("MessagesState", {...}):** A dict type with a single key **"messages"**.
- **Annotated[list, add_messages]:** The value is a **list** (of messages), and **add_messages** is the reducer: updates are merged by appending rather than replacing. So `return {"messages": [msg]}` from a node appends **msg** to state["messages"].
- **Use:** **MessagesState** is the minimal state type; the full **State** (below) extends this idea with more keys. The graph uses **State** everywhere; **MessagesState** may be used in tests or older code paths.

---

## 4. `ClassificationDecision` (lines 19–20)

```python
# Phase 5: classification from triage router.
ClassificationDecision = Literal["ignore", "notify", "respond"]
```

- **Comment:** Phase 5 added triage; the triage router (LLM) outputs one of these three decisions.
- **Literal["ignore", "notify", "respond"]:** A type that allows only these three string values. The triage node sets **state["classification_decision"]** to one of them:
  - **ignore** — Do nothing with the email.
  - **notify** — Show the user and optionally interrupt for a choice (respond vs ignore).
  - **respond** — Agent should reply (flow goes to prepare_messages → response_agent).

---

## 5. `State` (lines 22–34)

**Purpose:** Full graph state shared by all nodes. Holds messages, email payload, triage result, notify choice, and optional user message/question.

```python
# Phase 5: extended state for top-level graph (email mode + question mode).
State = TypedDict(
    "State",
    {
```

- **Comment:** Phase 5 extended state for the top-level graph, supporting both **email mode** (triage, reply to email) and **question mode** (plain chat).
- **TypedDict("State", {...}):** All keys are required in the type; at runtime some values may be **None** because they are **Optional**.

```python
        "messages": Annotated[list, add_messages],
```

- **messages:** Conversation history (HumanMessage, AIMessage, ToolMessage, etc.). Uses **add_messages** so nodes can return `{"messages": [new_msg]}` and it appends.

```python
        "email_input": Optional[dict],
```

- **email_input:** In **email mode**, this is set (e.g. by **input_router**) to a dict describing the email (subject, body, id, etc.). When present, the graph routes to the **email_assistant** subgraph (triage). When **None**, we’re in **question mode** and may go straight to **prepare_messages**.

```python
        "classification_decision": Optional[ClassificationDecision],
```

- **classification_decision:** Set by the **triage_router** node. One of **"ignore"**, **"notify"**, **"respond"**, or **None** (before triage or in question mode). Used by **\_after_triage_route** and **\_after_email_assistant_route** to decide the next step.

```python
        "email_id": Optional[str],
```

- **email_id:** Gmail message ID when replying to or triaging an email. Used by **mark_as_read_node** to mark that message as read, and possibly by tools (e.g. send reply).

```python
        "_notify_choice": Optional[str],  # "respond" | "ignore" after triage_interrupt (user resumes with Command(resume=...))
```

- **_notify_choice:** When classification is **notify**, **triage_interrupt_handler** calls **interrupt()**. The user resumes with a **Command(resume=...)** and the handler sets **_notify_choice** to **"respond"** or **"ignore"**. The leading underscore suggests internal use. **\_after_email_assistant_route** checks this to decide whether to go to **prepare_messages** or END.

```python
        "user_message": Optional[str],
        "question": Optional[str],
    },
)
```

- **user_message:** Optional raw user message (e.g. for question mode); **input_router** or the entrypoint may set it from input.
- **question:** Optional; alternative or additional field for the user’s question. Both **user_message** and **question** allow the graph to accept different input shapes (e.g. `{"question": "..."}` or `{"user_message": "..."}`).

---

## 6. `StateInput` (lines 36–46)

**Purpose:** Declares the **input schema** when invoking the graph. Only these keys are allowed; all are optional so callers can pass a subset (e.g. only `messages` and `question` for question mode).

```python
# Phase 5: input can be email payload (email mode) or user message (question mode).
StateInput = TypedDict(
    "StateInput",
    {
        "messages": Annotated[list, add_messages],
        "email_input": Optional[dict],
        "user_message": Optional[str],
        "question": Optional[str],
    },
    total=False,
)
```

- **Comment:** Input can be an **email payload** (email mode) or a **user message / question** (question mode).
- **StateInput** has the same keys as parts of **State** that are typically provided by the caller. **messages** uses **add_messages** so initial messages are merged correctly.
- **total=False:** Makes **all** keys optional. So the caller can pass `{}`, `{"question": "..."}`, `{"email_input": {...}}`, `{"messages": [...]}`, or any combination. The graph (e.g. **input_router**) normalizes this into **State**.

---

## 7. `RouterSchema` (lines 48–54)

**Purpose:** Structured output schema for the **triage** LLM. The model is asked to return an object with **reasoning** and **classification** so the graph can route reliably.

```python
# Phase 5: structured output from triage LLM.
RouterSchema = TypedDict(
    "RouterSchema",
    {
        "reasoning": str,
        "classification": ClassificationDecision,
    },
)
```

- **Comment:** Phase 5 triage uses structured output from the LLM.
- **reasoning:** Free-text explanation of why the model chose this classification (useful for debugging and transparency).
- **classification:** Must be one of **ClassificationDecision** (`"ignore"` | `"notify"` | `"respond"`). The triage node reads this and sets **state["classification_decision"]** to this value. Used with LLM **structured output** or parsing so the graph gets a fixed set of labels.

---

## 8. `NotifyChoiceSchema` (lines 56–60)

```python
# Phase 5: auto-decision when classification is notify (no HITL).
NotifyChoiceSchema = TypedDict(
    "NotifyChoiceSchema",
    {"choice": Literal["respond", "ignore"]},
)
```

- **Comment:** For notify, the schema describes the user’s (or an auto) **choice**: **respond** or **ignore**. The comment says “auto-decision when classification is notify (no HITL)”—so this schema can be used when the system decides without human-in-the-loop, or to describe the shape of the resume payload when HITL is used (user choice = respond | ignore).
- **choice:** Literal **"respond"** or **"ignore"**. Matches the values that **triage_interrupt_handler** writes into **state["_notify_choice"]**. Can be used to validate or structure the resume command or an auto-decision.

---

## 9. Flow summary (where schemas are used)

| Schema / Type            | Used by |
|--------------------------|--------|
| **State**                | All nodes and the top-level graph (`StateGraph(State)`). |
| **StateInput**           | Top-level graph as `input_schema=StateInput` for input validation. |
| **MessagesState**        | Minimal state; may be used by simple agent or tests. |
| **ClassificationDecision** | **State["classification_decision"]**, **RouterSchema["classification"]**, and routing logic. |
| **RouterSchema**         | Triage LLM structured output; parsed to set **classification_decision**. |
| **NotifyChoiceSchema**   | Notify choice (respond/ignore); aligns with **_notify_choice** and resume payload. |

---

## 10. Related files

- **Graph that uses State/StateInput:** `src/email_assistant/email_assistant_hitl_memory_gmail.py` (`StateGraph(State, input_schema=StateInput)`).
- **Nodes that read/write state:** `src/email_assistant/nodes/` (input_router, triage, triage_interrupt, prepare_messages, mark_as_read).
- **Triage using RouterSchema:** `src/email_assistant/nodes/triage.py` (sets **classification_decision** from LLM output).
- **add_messages:** LangGraph merges returned **messages** using this reducer; see [LangGraph docs](https://langchain-ai.github.io/langgraph/concepts/low_level/#state) on state and reducers.

For the graph structure and routing that use these fields, see **docs/code-explanations/email_assistant_hitl_memory_gmail.md**.
