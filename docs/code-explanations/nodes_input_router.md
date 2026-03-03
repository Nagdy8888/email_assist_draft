# Explanation: `nodes/input_router.py`

Detailed walkthrough of the **input_router** node: it normalizes incoming input and sets **messages** and **email_input** so the graph can route to the email path (triage) or the question path (response agent). Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–6)

```python
"""
input_router: route by email_input vs user_message/question (email path vs question path).

Use cases: entry node that normalizes input into state; conditional edge from this node
sends to triage_router when email_input is present, else to response_agent (question mode).
"""
```

- **Line 2:** This module defines **input_router**, which routes based on whether the input is **email_input** (email to triage/reply) or **user_message** / **question** (plain question).
- **Lines 4–5:** **Use cases:** This node is the **first node after START**. It normalizes the raw input into **state** (messages, email_input). The **conditional edge** that runs after this node (in **email_assistant_hitl_memory_gmail.py**) checks **state["email_input"]**: if present → **email_assistant** subgraph (triage); otherwise → **prepare_messages** (question mode → response_agent).

---

## 2. Imports (lines 8–10)

```python
from langchain_core.messages import HumanMessage
```

- **HumanMessage:** Used to wrap the user’s text when we’re in question mode. The node sets **messages** to a single **HumanMessage(content=user_message)** so the response subgraph has one user turn to reply to.

```python
from email_assistant.schemas import State
```

- **State:** Typed state dict. The node reads **messages**, **user_message**, **question**, **email_input** from state and returns a **dict** of updates that LangGraph merges into state.

---

## 3. `_normalize_email_input` (lines 13–55)

**Purpose:** Turn raw **email_input** (from Studio, CLI, or Gmail API) into a single normalized dict with **from**, **to**, **subject**, **body**, and optionally **id** and **_source**. Supports both a flat dict (Studio/mock) and a Gmail API–style payload.

```python
def _normalize_email_input(email_input: dict | None) -> dict | None:
    """Ensure email_input has from, to, subject, body; support Gmail-style payload or flat dict.
    Sets _source to 'gmail' when the payload has a Gmail message id or Gmail API structure so the agent knows it is an incoming message from the user's Gmail inbox."""
```

- **email_input:** Raw input: either a flat dict with from/to/subject/body (and optional id) or a Gmail API–style object (e.g. with **payload**, **payload.headers**).
- **Returns:** A normalized dict with keys **from**, **to**, **subject**, **body**, **id** (optional), and **_source** (optional, `"gmail"`). Returns **None** if input is invalid.

```python
    if not email_input or not isinstance(email_input, dict):
        return None
```

- If **email_input** is missing, empty, or not a dict, we can’t normalize it → return **None**. The caller will then leave **email_input** unchanged or not set it.

```python
    # Unwrap double-nested email_input (e.g. Studio run input sometimes as {"email_input": {"email_input": {...}}}).
    if set(email_input.keys()) <= {"email_input"} and isinstance(email_input.get("email_input"), dict):
        email_input = email_input["email_input"]
```

- **Double-nesting:** Sometimes the run input is shaped like **{"email_input": {"email_input": {...}}}**. If the top-level dict’s only key is **"email_input"** and its value is a dict, we unwrap once so the rest of the code works on the inner **email_input** dict.

```python
    has_gmail_id = bool(email_input.get("id"))
    payload = email_input.get("payload") or {}
    headers = payload.get("headers") or []
    is_gmail_api = bool(payload or headers)
    from_gmail = has_gmail_id or is_gmail_api
```

- **has_gmail_id:** True if the dict has an **id** (Gmail message id).
- **payload / headers:** From Gmail API structure: **payload** is the message payload, **headers** is the list of header objects.
- **is_gmail_api:** True if we have a **payload** or **headers** (Gmail API shape).
- **from_gmail:** True if we have a Gmail id or Gmail API structure. When True, we set **"_source": "gmail"** in the output so downstream (e.g. triage) knows this is an incoming Gmail message.

```python
    # Flat dict (Studio/mock)
    if "from" in email_input or "subject" in email_input:
        out = {
            "from": email_input.get("from", ""),
            "to": email_input.get("to", ""),
            "subject": email_input.get("subject", ""),
            "body": email_input.get("body", email_input.get("snippet", "")),
            "id": email_input.get("id"),
        }
        if from_gmail:
            out["_source"] = "gmail"
        return out
```

- **Flat dict path:** If the dict already has **from** or **subject**, we treat it as a flat Studio/mock payload. We build **out** with **from**, **to**, **subject**, **body** (body or snippet), **id**. If **from_gmail** is True (e.g. **id** was set), we add **"_source": "gmail"** and return.

```python
    # Gmail API payload: payload.headers + id, threadId
    def h(name: str) -> str:
        for x in headers:
            if (x.get("name") or "").lower() == name.lower():
                return (x.get("value") or "").strip()
        return ""
```

- **h(name):** Helper that finds a header in **headers** by **name** (case-insensitive) and returns its **value** (stripped), or **""** if not found. Used for **From**, **To**, **Subject** in the Gmail API path.

```python
    out = {
        "from": h("from"),
        "to": h("to"),
        "subject": h("subject"),
        "body": email_input.get("snippet") or payload.get("body", {}).get("data") or "",
        "id": email_input.get("id"),
    }
    if from_gmail:
        out["_source"] = "gmail"
    return out
```

- **Gmail API path:** When the dict didn’t have flat **from**/ **subject**, we treat it as Gmail API: **from**, **to**, **subject** come from **h("from")**, **h("to")**, **h("subject")**. **body** is **snippet** (top-level) or **payload.body.data** (decoded body), or **""**. **id** is the top-level message id. We set **_source** to **"gmail"** when **from_gmail** is True, then return **out**.

---

## 4. `input_router` (lines 57–79)

**Purpose:** First node after START. Normalizes input: if the user provided **user_message** or **question**, set **messages** to a single **HumanMessage**. If **email_input** is provided, normalize it and set **email_input** (and **email_id** when present). The returned dict is merged into state; the conditional edge uses **email_input** to choose email path vs question path.

```python
def input_router(state: State) -> dict:
    """
    Normalize input: if user_message or question provided, set messages to a single HumanMessage.
    Return state update; do not change email_input (used by conditional edge for routing).

    Use cases: first node after START; ensures messages exist for question path and
    email_input is normalized for triage path.
    """
```

- **state:** Current graph state (may already have **messages**, **user_message**, **question**, **email_input** from the initial input).
- **Returns:** A **dict** of updates; LangGraph merges this into state (e.g. **messages** is replaced by the reducer behavior; **email_input** and **email_id** are set if we normalize an email).
- **Docstring:** In question mode we set **messages** to one **HumanMessage**. We only set **email_input** when we successfully normalize it; the conditional edge reads **state["email_input"]** to route.

```python
    updates: dict = {}
    messages = list(state.get("messages") or [])
```

- **updates:** Accumulates the keys we will return (messages, email_input, email_id).
- **messages:** Copy of **state["messages"]** or an empty list. We may replace it with a single **HumanMessage** when **user_message** or **question** is provided.

```python
    user_message = state.get("user_message") or state.get("question")
    if user_message and isinstance(user_message, str):
        messages = [HumanMessage(content=user_message)]
        updates["messages"] = messages
```

- **user_message:** From state **user_message** or **question** (caller can pass either key for the user’s text).
- If **user_message** is a non-empty string, we set **messages** to a single **HumanMessage** with that content and put it in **updates**. So in question mode, the response agent sees exactly one user message to reply to. If the user didn’t pass **user_message** or **question**, we leave **messages** as-is (e.g. from initial input).

```python
    email_input = state.get("email_input")
    if email_input is not None:
        normalized = _normalize_email_input(email_input)
        if normalized:
            updates["email_input"] = normalized
            if normalized.get("id"):
                updates["email_id"] = str(normalized["id"])
```

- **email_input:** Raw email payload from state (may be flat or Gmail API).
- If **email_input** is present, we call **_normalize_email_input**. If normalization succeeds, we set **updates["email_input"]** to the normalized dict. If that dict has **id**, we also set **updates["email_id"]** to the string form of the id (for **mark_as_read_node** and tools that need the Gmail message id).

```python
    return updates
```

- Return the updates dict. LangGraph merges it into state. The **conditional edge** after this node (**_after_input_router_route**) checks **state.get("email_input")**: truthy → **email_assistant** (triage path); else → **prepare_messages** (question path).

---

## 5. Flow summary

1. **input_router** runs first after START with the initial **state** (from graph input).
2. **Question path:** If **user_message** or **question** is set and is a string → **updates["messages"]** = **[HumanMessage(content=...)]**. No **email_input** → conditional edge sends to **prepare_messages** → response_agent.
3. **Email path:** If **email_input** is present → normalize with **_normalize_email_input**. If valid → **updates["email_input"]** = normalized dict; if it has **id** → **updates["email_id"]** = id string. Conditional edge sees **email_input** → sends to **email_assistant** subgraph (triage).
4. **Normalization** supports: flat dict (from/subject/body/id), double-wrapped **email_input**, and Gmail API (payload.headers, snippet/body.data). **_source** is set to **"gmail"** when the payload looks like Gmail so triage can treat it as an incoming inbox message.

---

## 6. Related files

- **State / StateInput:** `src/email_assistant/schemas.py` (State has **messages**, **email_input**, **email_id**, **user_message**, **question**).
- **Graph wiring:** `src/email_assistant/email_assistant_hitl_memory_gmail.py` (START → input_router; conditional edge uses **email_input** to route to email_assistant vs prepare_messages).
- **Triage:** `src/email_assistant/nodes/triage.py` (uses normalized **email_input** with from/to/subject/body and **_source** for the triage prompt).
- **mark_as_read:** `src/email_assistant/nodes/mark_as_read.py` (uses **email_id** to mark the Gmail message read).

For the top-level flow and routing, see **docs/code-explanations/email_assistant_hitl_memory_gmail.md**. For state shape, see **docs/code-explanations/schemas.md**.
