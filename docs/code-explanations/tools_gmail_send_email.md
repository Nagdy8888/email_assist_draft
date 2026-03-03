# Explanation: `tools/gmail/send_email.py`

Detailed walkthrough of **send_email_tool**: the LangChain tool that sends new emails or replies via the Gmail API, plus the helpers **send_new_email** and **send_reply_email**. Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–6)

```python
"""
send_email_tool: send new email to a given address (Phase 4); reply by email_id (Phase 5).

Use cases: Gmail API to send new message or reply in thread; used by response agent
when user asks to "email X with subject Y" or when replying to triaged email.
"""
```

- **Line 2:** This module defines **send_email_tool**: send a **new** email to an address (Phase 4) or send a **reply** in a thread using **email_id** (Phase 5).
- **Lines 4–5:** **Use cases:** The Gmail API is used to send either a new message or a reply in the same thread. The response agent calls this when the user says “email X with subject Y” (new) or when replying to a triaged email (reply with **email_id** from **prepare_messages**).

---

## 2. Imports (lines 8–14)

```python
import base64
from email.mime.text import MIMEText
from typing import Optional
```

- **base64:** Gmail API expects the message body as **base64url**-encoded raw RFC 2822. We use **base64.urlsafe_b64encode(...).decode()** to produce the **raw** string.
- **MIMEText:** Build a MIME text message (To, Subject, body). We set headers and call **.as_bytes()** to get the raw bytes for encoding.
- **Optional:** Used for **email_id: Optional[str] = None** in **send_email_tool** so the tool can be called with or without **email_id** (new vs reply).

```python
from langchain_core.tools import tool
from email_assistant.tools.gmail.auth import get_gmail_service
```

- **tool:** Decorator that turns **send_email_tool** into an LLM-callable tool (name, description, and parameters from the function signature and docstring).
- **get_gmail_service:** Returns the Gmail API v1 service (credentials from **auth.py**). Used in **send_new_email** and **send_reply_email** to call **users().messages().send()** and **.get()**.

---

## 3. `_get_header` (lines 17–23)

```python
def _get_header(headers: list[dict], name: str) -> str:
    """Get first header value by name (case-insensitive)."""
    name_lower = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name_lower:
            return (h.get("value") or "").strip()
    return ""
```

- **Purpose:** From a Gmail API **headers** list (each item has **"name"** and **"value"**), return the value of the first header whose name matches **name** (case-insensitive). Used in **send_reply_email** to read **Message-ID** and **Subject** from the original message.
- **name_lower:** Normalize the requested header name for comparison.
- **Loop:** Find the first header with matching **name**, return its **value** (stripped), or **""** if not found.

---

## 4. `send_new_email` (lines 26–39)

**Purpose:** Send a new email (no thread). Build a MIMEText message, encode it as base64url, and call Gmail **users().messages().send()** with **userId="me"**. Used when the agent sends to a recipient without replying to an existing message.

```python
def send_new_email(to_email: str, subject: str, body: str) -> str:
    """
    Send a new email via Gmail API (no reply thread).

    Use cases: called by send_email_tool when email_id is not provided.
    """
```

- **to_email, subject, body:** Recipient address, subject line, and body text. The agent fills these from the user’s request or its own draft.
- **Returns:** A short confirmation string (e.g. “Email sent to … (message id: …)”) that becomes the tool result in the conversation.

```python
    service = get_gmail_service()
```

- **service:** Gmail API v1 service (from **auth.get_gmail_service()**). Uses the OAuth credentials (token/refresh) from **auth.py**.

```python
    message = MIMEText(body)
    message["to"] = to_email
    message["subject"] = subject
```

- **MIMEText(body):** Creates a MIME text/plain message with the given body.
- **message["to"]**, **message["subject"]:** Set To and Subject headers so the sent email has the correct recipient and subject.

```python
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return f"Email sent to {to_email} (message id: {sent.get('id', '')})."
```

- **raw:** The full RFC 2822 message (including headers and body) as bytes, then base64url-encoded and decoded to a string. Gmail API requires this format for **raw**.
- **send(userId="me", body={"raw": raw}):** Sends the message as the authenticated user. **"me"** is the standard alias for the current user. **.execute()** performs the request and returns the created message resource (with **id**, etc.).
- **return:** Confirmation string including the new message id so the agent (and user) know the send succeeded.

---

## 5. `send_reply_email` (lines 42–69)

**Purpose:** Send a reply in the same Gmail thread. Fetches the original message to get **threadId** and **Message-ID**, builds a reply with **In-Reply-To** and **References**, and sends with **threadId** so Gmail keeps the conversation in one thread.

```python
def send_reply_email(email_id: str, to_email: str, subject: str, body: str) -> str:
    """
    Send a reply in the same Gmail thread. Fetches original message for threadId and Message-ID.

    Use cases: called by send_email_tool when email_id is provided; keeps thread continuity.
    """
```

- **email_id:** Gmail message id of the message we’re replying to (set by **input_router** / **prepare_messages** on the respond path).
- **to_email, subject, body:** Recipient (often the original From), subject (may be “Re: …”), and reply body.
- **Returns:** A short confirmation string that becomes the tool result.

```python
    service = get_gmail_service()
    orig = service.users().messages().get(userId="me", id=email_id, format="full").execute()
```

- **get(userId="me", id=email_id, format="full"):** Fetches the full original message (headers and body). We need it for **threadId** and **Message-ID** (and optionally **Subject** for “Re:”).

```python
    payload = orig.get("payload") or {}
    headers = payload.get("headers") or []
    thread_id = orig.get("threadId", "")
    message_id_header = _get_header(headers, "Message-ID")
    orig_subject = _get_header(headers, "Subject")
```

- **payload / headers:** Gmail API stores headers inside **payload.headers**. We use **_get_header** to get **Message-ID** (for **In-Reply-To** / **References**) and **Subject** (to build **Re: …** if the agent didn’t already).
- **thread_id:** From the top-level **orig** so we can send the reply in the same thread.

```python
    reply_subject = f"Re: {orig_subject}" if orig_subject and not subject.strip().lower().startswith("re:") else (subject or f"Re: {orig_subject}")
```

- **reply_subject:** If the agent provided a subject that doesn’t already start with “re:”, and we have **orig_subject**, use **"Re: {orig_subject}"**. Otherwise use the agent’s **subject** or fallback **"Re: {orig_subject}"**. Keeps reply subjects consistent (e.g. “Re: Q4 report request”).

```python
    message = MIMEText(body)
    message["to"] = to_email
    message["subject"] = reply_subject
    if message_id_header:
        message["In-Reply-To"] = message_id_header
        message["References"] = message_id_header
```

- **MIMEText / to / subject:** Build the reply message with the chosen subject.
- **In-Reply-To** and **References:** Set to the original **Message-ID** so mail clients (and Gmail) treat this as a reply and show it in the same thread. **References** is set to the same value here (minimal; some clients expect a chain).

```python
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body_send = {"raw": raw}
    if thread_id:
        body_send["threadId"] = thread_id
    sent = service.users().messages().send(userId="me", body=body_send).execute()
    return f"Reply sent in thread (message id: {sent.get('id', '')})."
```

- **raw:** Base64url-encoded reply message.
- **body_send:** **raw** is required; **threadId** is added when we have it so Gmail places the reply in the same thread.
- **send(...).execute():** Sends the reply; returns the new message resource.
- **return:** Confirmation string for the tool result.

---

## 6. `send_email_tool` (lines 72–91)

**Purpose:** LangChain tool that the response agent calls to send email. If **email_id** is provided, delegate to **send_reply_email**; otherwise to **send_new_email**. The docstring tells the LLM when to use **email_address**/subject/body and when to also pass **email_id**.

```python
@tool
def send_email_tool(
    email_address: str,
    subject: str,
    body: str,
    email_id: Optional[str] = None,
) -> str:
```

- **@tool:** Registers the function as a tool; the LLM sees **send_email_tool** with parameters **email_address**, **subject**, **body**, and optional **email_id**.
- **email_address:** Recipient address (required). For replies this is typically the original sender (From).
- **subject, body:** Subject and body of the email (or reply).
- **email_id:** Optional. When set (e.g. from **prepare_messages** context), we send a reply in thread; when None, we send a new email.

```python
    """
    Send an email. Use for NEW emails: provide email_address (recipient), subject, and body.
    For replying to an existing email, provide email_id as well (Phase 5).
    """
```

- **Docstring:** Becomes the tool description for the LLM. Instructs: for **new** emails use **email_address**, **subject**, **body**; for **replying** also provide **email_id** (Phase 5 reply path). This matches **prompts.get_agent_system_prompt_with_tools** (“do not use email_id for new emails”; “use send_email_tool with email_id as well” when replying).

```python
    if email_id:
        return send_reply_email(
            email_id=email_id,
            to_email=email_address,
            subject=subject,
            body=body,
        )
    return send_new_email(to_email=email_address, subject=subject, body=body)
```

- **if email_id:** When the agent is replying (e.g. “reply to this email”), **email_id** is in state and the prompt tells the agent to pass it. We call **send_reply_email** with **email_id**, **email_address** (to), **subject**, **body**.
- **else:** New email; call **send_new_email** with the same **email_address**, **subject**, **body**. Return value from either path becomes the tool result (ToolMessage) in the conversation.

---

## 7. Flow summary

1. **send_email_tool** is in **get_tools(include_gmail=True)** and is bound to the LLM in the response subgraph. The agent calls it with **email_address**, **subject**, **body**, and optionally **email_id**.
2. **New email:** **email_id** is None → **send_new_email** → MIMEText, base64url, **users().messages().send(userId="me", body={"raw": raw})** → return confirmation.
3. **Reply:** **email_id** is set → **send_reply_email** → **users().messages().get()** for threadId and Message-ID → build reply with In-Reply-To/References and reply_subject → **send(..., body={"raw": raw, "threadId": thread_id})** → return confirmation.
4. **prepare_messages** injects “Use send_email_tool with email_id='...' to send your reply” so the agent has **email_id** in context when replying to a triaged email.

---

## 8. Related files

- **Auth:** `src/email_assistant/tools/gmail/auth.py` (**get_gmail_service**).
- **Tool list:** `src/email_assistant/tools/__init__.py` (**get_tools** includes **send_email_tool**).
- **Response agent / prompt:** `src/email_assistant/simple_agent.py`, `src/email_assistant/prompts.py` (when to use send_email_tool with/without email_id).
- **Reply context:** `src/email_assistant/nodes/prepare_messages.py` (injects **email_id** and reply instructions into messages).

For auth and service building, see **docs/code-explanations/tools_gmail_auth.md**. For the tool list and agent prompt, see **docs/code-explanations/tools_init.md** and **docs/code-explanations/prompts.md**.
