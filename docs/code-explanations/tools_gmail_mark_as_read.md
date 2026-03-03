# Explanation: `tools/gmail/mark_as_read.py`

Detailed walkthrough of **mark_as_read**: the Gmail API helper that marks a message as read by removing the **UNREAD** label. It is called by **mark_as_read_node** after the response_agent finishes in email mode. Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–6)

```python
"""
mark_as_read: Gmail API call to mark a message as read by id.

Use cases: called from mark_as_read node after response_agent finishes for email mode.
Requires gmail.modify scope.
"""
```

- **Line 2:** This module exposes **mark_as_read**: a single Gmail API call that marks a message as read using its **id**.
- **Lines 4–5:** **Use cases:** The **mark_as_read_node** (in **nodes/mark_as_read.py**) calls this after the **response_agent** subgraph finishes when we're in **email mode** (triage/reply path). So the email we triaged and possibly replied to is marked read in the user's inbox.
- **Line 5:** The Gmail API method used (**users().messages().modify()** with **removeLabelIds**) requires the **gmail.modify** OAuth scope, which is included in **auth.SCOPES**.

---

## 2. Import (line 8)

```python
from email_assistant.tools.gmail.auth import get_gmail_service
```

- **get_gmail_service:** Returns the Gmail API v1 service (credentials from **auth.py**). We use it to call **users().messages().modify()** for the authenticated user.

---

## 3. `mark_as_read` (lines 11–26)

**Purpose:** For a given Gmail message **email_id**, call the Gmail API to remove the **UNREAD** label so the message appears as read. If **email_id** is missing or blank, return a message without calling the API.

```python
def mark_as_read(email_id: str) -> str:
    """
    Mark the Gmail message with the given id as read (remove UNREAD label).

    Use cases: after the agent has replied to an email, mark the original as read.
    """
```

- **email_id:** Gmail message id (string). Same id set by **input_router** from **email_input["id"]** and used by **prepare_messages** and **send_reply_email**.
- **Returns:** A short status string: either “No email_id provided; nothing to mark as read.” or “Message {email_id} marked as read.” The node uses this for logging/feedback; **mark_as_read_node** ignores the return value and always returns **{}** to state.
- **Docstring:** Describes the effect (remove UNREAD) and the typical use (after the agent has replied, mark the original as read).

```python
    if not email_id or not email_id.strip():
        return "No email_id provided; nothing to mark as read."
```

- **Guard:** If **email_id** is None, empty, or only whitespace, we don’t call the API. Return a clear message so callers know nothing was done. **mark_as_read_node** already checks **state.get("email_id")** before calling this, so this guard is a safety check if the function is used elsewhere.

```python
    service = get_gmail_service()
```

- **service:** Gmail API v1 service for the authenticated user (OAuth from **auth.get_credentials()**). Used for **users().messages().modify()**.

```python
    service.users().messages().modify(
        userId="me",
        id=email_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()
```

- **users().messages().modify(...):** Gmail API method that updates a message’s labels. We don’t change the message body or headers; we only change labels.
- **userId="me":** Standard alias for the authenticated user’s mailbox.
- **id=email_id:** The message to update (the triaged/replied-to message).
- **body={"removeLabelIds": ["UNREAD"]}:** Remove the **UNREAD** label. In Gmail, a message without **UNREAD** is shown as read. We don’t add any labels; only remove **UNREAD**.
- **.execute():** Sends the request. Raises if the API errors (e.g. invalid id, network, auth). **mark_as_read_node** catches exceptions and doesn’t fail the graph.

```python
    return f"Message {email_id} marked as read."
```

- **Return:** Confirmation string. The node doesn’t use it for state; it can be used for logs or debugging.

---

## 4. Flow summary

1. **mark_as_read_node** runs after **response_agent** (graph: response_agent → mark_as_read → END). It reads **state["email_id"]** (set by **input_router** on the email path).
2. If **email_id** is set, the node calls **mark_as_read(str(email_id))** from this module. If not set (question-only run), the node returns **{}** and never calls this function.
3. **mark_as_read** checks **email_id**; gets **get_gmail_service()**; calls **users().messages().modify(userId="me", id=email_id, body={"removeLabelIds": ["UNREAD"]}).execute()**; returns a status string.
4. If the Gmail API call fails, **mark_as_read_node** catches the exception and returns **{}** so the graph still completes; only the “mark as read” step is skipped.

---

## 5. Related files

- **Auth / scopes:** `src/email_assistant/tools/gmail/auth.py` (**get_gmail_service**, **SCOPES** including **gmail.modify**).
- **Node that calls this:** `src/email_assistant/nodes/mark_as_read.py` (**mark_as_read_node** calls **gmail_mark_as_read** = this **mark_as_read**).
- **Where email_id comes from:** `src/email_assistant/nodes/input_router.py` (sets **email_id** from normalized **email_input["id"]**).

For the node that invokes this, see **docs/code-explanations/nodes_mark_as_read.md**. For auth and scopes, see **docs/code-explanations/tools_gmail_auth.md**.
