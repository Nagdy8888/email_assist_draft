# Explanation: `nodes/mark_as_read.py`

Detailed walkthrough of the **mark_as_read_node**: when **email_id** is present in state, it marks that Gmail message as read; otherwise it does nothing. Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–6)

```python
"""
mark_as_read_node: mark email as read when email_id present; no-op when no email_id.

Use cases: after response_agent finishes, mark the source email read in Gmail
for email mode; question-only mode has no email_id so this node no-ops.
"""
```

- **Line 2:** This module implements **mark_as_read_node**, which **marks the email as read** in Gmail when **email_id** is set. When **email_id** is missing or empty, the node does nothing (no-op).
- **Lines 4–5:** **Use cases:** The node runs **after** the **response_agent** subgraph. In **email mode** (triage/reply path), **email_id** is set by **input_router**, so we call the Gmail API to mark that message read. In **question-only mode** there is no email, so **email_id** is not set and the node returns without calling the API.

---

## 2. Imports (lines 8–9)

```python
from email_assistant.schemas import State
from email_assistant.tools.gmail.mark_as_read import mark_as_read as gmail_mark_as_read
```

- **State:** Graph state type. The node only reads **email_id** and returns **{}** (no state update).
- **gmail_mark_as_read:** Function from the Gmail tools that performs the “mark as read” API call for a given message id. Imported as **gmail_mark_as_read** to avoid clashing with the node name **mark_as_read_node**.

---

## 3. `mark_as_read_node` (lines 12–26)

**Purpose:** If **state["email_id"]** is set and non-empty, call **gmail_mark_as_read(email_id)** to mark that Gmail message as read. Otherwise return without doing anything. Errors from the Gmail API are swallowed so the graph always completes.

```python
def mark_as_read_node(state: State) -> dict:
    """
    Call Gmail mark_as_read(email_id) when state has email_id; otherwise no-op.

    Use cases: run after response_agent on the respond path so the triaged email is marked read.
    """
```

- **state:** Current graph state. We only use **email_id** (set by **input_router** when the normalized email had an id).
- **Returns:** Always **{}** — this node does not change state; it only has a side effect (Gmail API call). Returning **{}** means LangGraph merges nothing into state.
- **Docstring:** On the respond path we run after **response_agent** so the email we triaged and (optionally) replied to is marked read in Gmail.

```python
    email_id = state.get("email_id")
    if not email_id or not str(email_id).strip():
        return {}
```

- **email_id:** The Gmail message id (string or value that can be stringified). Set by **input_router** when **email_input** had an **id**.
- **Guard:** If **email_id** is missing, None, or an empty/whitespace string after **str(...).strip()**, we return **{}** and do not call the Gmail API. So in question-only runs (no email) we no-op and the graph continues to END.

```python
    try:
        gmail_mark_as_read(str(email_id))
    except Exception:
        pass  # Don't fail the graph if Gmail API fails
```

- **gmail_mark_as_read(str(email_id)):** Calls the Gmail tool with the message id as a string. The underlying implementation (in **email_assistant.tools.gmail.mark_as_read**) uses the Gmail API to set the message’s “read” label or remove the UNREAD label.
- **except Exception: pass:** If the call fails (e.g. network error, invalid id, quota, auth), we ignore the error and do not re-raise. The graph still finishes and returns to the user; only the “mark as read” step is skipped. This keeps a single Gmail API failure from failing the whole run.

```python
    return {}
```

- Return an empty update so state is unchanged. The node is side-effect only.

---

## 4. Flow summary

1. **mark_as_read_node** runs after **response_agent** on every run (graph edge: response_agent → mark_as_read → END).
2. **Email/respond path:** **email_id** was set by **input_router** and is still in state. The node calls **gmail_mark_as_read(email_id)** so the triaged (and possibly replied-to) email is marked read in Gmail. Then returns **{}**.
3. **Question path:** **email_id** is not set. The node returns **{}** immediately (no API call).
4. Any Gmail API error is caught and ignored; the graph always proceeds to END.

---

## 5. Related files

- **State / email_id:** `src/email_assistant/schemas.py` (**State** has **email_id**).
- **Graph wiring:** `src/email_assistant/email_assistant_hitl_memory_gmail.py` (response_agent → mark_as_read → END).
- **input_router:** `src/email_assistant/nodes/input_router.py` (sets **email_id** from normalized **email_input["id"]**).
- **Gmail tool:** `src/email_assistant/tools/gmail/mark_as_read.py` (**mark_as_read** — actual Gmail API call).

For the top-level flow, see **docs/code-explanations/email_assistant_hitl_memory_gmail.md**. For state, see **docs/code-explanations/schemas.md**.
