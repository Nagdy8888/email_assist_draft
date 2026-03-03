# Explanation: `tools/gmail/fetch_emails.py`

Detailed walkthrough of **fetch_emails**: helpers to list Gmail INBOX message ids and to turn a Gmail message into the **email_input** shape used by the graph. Used by the Gmail watcher script to feed real emails into the agent. Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–7)

```python
"""
Fetch emails from Gmail for automatic ingestion into the agent.

Use cases: list recent/unread inbox messages; convert a Gmail message to email_input
so the graph can run triage and response. Used by the Gmail watcher script to feed
real emails into the agent automatically.
"""
```

- **Line 2:** This module provides **fetching** of emails from Gmail so they can be passed into the agent as **email_input**.
- **Lines 4–6:** **Use cases:** List recent or unread INBOX messages; convert a Gmail API message into the **email_input** dict shape (from, to, subject, body, id) so the graph can run **input_router** → triage → response. The **Gmail watcher script** (e.g. **watch_gmail.py**) uses these functions to pull real emails and invoke the graph with **{"email_input": ...}** so the agent triages and optionally replies automatically.

---

## 2. Imports (lines 9–12)

```python
import base64
from typing import Optional
```

- **base64:** Gmail API returns message body (and parts) as **base64url**-encoded strings. We use **base64.urlsafe_b64decode(...)** to get bytes, then decode to UTF-8 text in **_decode_body**.
- **Optional:** Used for **get_message_as_email_input** return type (**Optional[dict]**) and **list_inbox_message_ids** parameter **query: Optional[str] = None**.

```python
from email_assistant.tools.gmail.auth import get_gmail_service
```

- **get_gmail_service:** Used in **fetch_recent_inbox** when no service is passed (default). The Gmail watcher or other callers can pass a pre-built service to avoid creating it multiple times.

---

## 3. `_header` (lines 15–21)

```python
def _header(msg: dict, name: str) -> str:
    """Get a header value from Gmail message payload."""
    payload = msg.get("payload") or {}
    for h in payload.get("headers") or []:
        if (h.get("name") or "").lower() == name.lower():
            return (h.get("value") or "").strip()
    return ""
```

- **Purpose:** From a Gmail API **message** dict (with **payload.headers**), return the value of the first header whose **name** matches **name** (case-insensitive). Used in **get_message_as_email_input** to get **From**, **To**, **Subject**.
- **payload:** **msg["payload"]**; Gmail puts headers in **payload.headers** (list of **{name, value}**).
- **Loop:** Find first header with matching name, return stripped value; otherwise **""**.

---

## 4. `_decode_body` (lines 24–47)

**Purpose:** Extract plain text body from a Gmail **payload** dict. Handles single-part (payload.body.data) and multipart (first text/plain or text/html part). Decodes base64url to UTF-8; on decode errors returns empty string or skips the part.

```python
def _decode_body(payload: dict) -> str:
    """Extract plain text body from Gmail payload (single or multipart)."""
    if not payload:
        return ""
```

- **payload:** The **payload** object from **msg.get("payload")** (headers, body, parts).
- **Early return:** No payload → **""**.

```python
    # Single-part: payload.body.data (base64url)
    body = payload.get("body") or {}
    data = body.get("data")
    if data:
        try:
            return base64.urlsafe_b64decode(data.encode("ASCII")).decode("utf-8", errors="replace")
        except Exception:
            return ""
```

- **Single-part:** Many messages have **payload.body.data** (base64url string). Decode with **base64.urlsafe_b64decode(data.encode("ASCII"))** then **.decode("utf-8", errors="replace")** so invalid UTF-8 is replaced instead of raising. On any exception return **""**.

```python
    # Multipart: find first text/plain or text/html part
    for part in payload.get("parts") or []:
        mimetype = (part.get("mimeType") or "").lower()
        if "text/plain" in mimetype or "text/html" in mimetype:
            part_body = part.get("body") or {}
            part_data = part_body.get("data")
            if part_data:
                try:
                    return base64.urlsafe_b64decode(part_data.encode("ASCII")).decode("utf-8", errors="replace")
                except Exception:
                    pass
    return ""
```

- **Multipart:** If there was no single **body.data**, iterate **payload.parts**. For the first part whose **mimeType** contains **text/plain** or **text/html**, decode **part.body.data** the same way and return it. Prefer first matching part; no strip of HTML tags here (body may be HTML). If nothing is found or decoding fails, return **""**.

---

## 5. `get_message_as_email_input` (lines 50–73)

**Purpose:** Fetch one Gmail message by **message_id** and return it as an **email_input**-shaped dict (from, to, subject, body, id) for the graph. **input_router** will normalize it and set **_source** to **"gmail"** when it sees this shape. Returns **None** if the message can’t be fetched.

```python
def get_message_as_email_input(service, message_id: str) -> Optional[dict]:
    """
    Fetch a Gmail message by id and return it in email_input shape for the graph.

    Returns dict with from, to, subject, body, id (and _source will be set by input_router).
    Returns None if the message cannot be fetched.
    """
```

- **service:** Gmail API v1 service (from **get_gmail_service()** or passed by caller).
- **message_id:** Gmail message id (string).
- **Returns:** Dict with keys **from**, **to**, **subject**, **body**, **id** — the same shape **input_router._normalize_email_input** expects for a “flat” dict. **input_router** will add **_source: "gmail"** when it detects Gmail (e.g. presence of **id**). Returns **None** on fetch failure.

```python
    try:
        msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    except Exception:
        return None
```

- **get(userId="me", id=message_id, format="full"):** Fetches the full message (headers + body). Any exception (network, 404, auth) → return **None**.

```python
    payload = msg.get("payload") or {}
    body = _decode_body(payload)
    snippet = (msg.get("snippet") or "").strip()
    if not body and snippet:
        body = snippet
```

- **body:** Decoded from payload (single or multipart) via **_decode_body**.
- **snippet:** Gmail’s short plain-text snippet (often the first line of the body). If **body** is empty (e.g. image-only or decode failed), use **snippet** as the body so the graph still has some content for triage.

```python
    return {
        "from": _header(msg, "From"),
        "to": _header(msg, "To"),
        "subject": _header(msg, "Subject"),
        "body": body[:8000] if body else snippet[:8000],
        "id": msg.get("id"),
    }
```

- **from, to, subject:** From **payload.headers** via **_header**.
- **body:** Use decoded **body** or **snippet**, truncated to **8000** characters to keep payload size and token usage reasonable (same cap as in triage/prepare_messages).
- **id:** Gmail message id so the graph can use it for **email_id** (reply, mark_as_read). **input_router** will set **state["email_id"]** from this.

---

## 6. `list_inbox_message_ids` (lines 76–101)

**Purpose:** List message ids from the user’s INBOX using the Gmail API **messages.list**. Supports limiting count, unread-only, and an optional query. Used by the watcher to get a set of ids to then fetch and turn into **email_input** dicts.

```python
def list_inbox_message_ids(
    service,
    max_results: int = 20,
    unread_only: bool = False,
    query: Optional[str] = None,
) -> list[str]:
    """
    List message ids from the user's INBOX.

    Use cases: watcher uses this to find new emails to process.
    """
```

- **service:** Gmail API v1 service.
- **max_results:** Max number of message ids to return (default 20). Gmail API **maxResults** cap applies.
- **unread_only:** If True, restrict to unread messages (**q="is:unread"**).
- **query:** Optional Gmail search query (e.g. **"newer_than:1d"**). Combined with **is:unread** when **unread_only** is True.
- **Returns:** List of message id strings (order depends on API; often newest first).

```python
    label_ids = ["INBOX"]
    q = "is:unread" if unread_only else None
    if query:
        q = f"{q} {query}".strip() if q else query
```

- **label_ids:** Restrict to **INBOX** (user’s inbox).
- **q:** Search query. If **unread_only**, start with **"is:unread"**; if **query** is also set, append it (e.g. **"is:unread newer_than:1d"**). If not unread_only but **query** is set, **q** is just **query**.

```python
    try:
        result = service.users().messages().list(
            userId="me",
            labelIds=label_ids,
            maxResults=max_results,
            q=q,
        ).execute()
    except Exception as e:
        raise RuntimeError(f"Gmail API list failed: {e}") from e
    return [m["id"] for m in result.get("messages", [])]
```

- **list(userId="me", labelIds=label_ids, maxResults=max_results, q=q):** Gmail API list; **q** can be None (Gmail accepts it). **.execute()** returns a dict with **messages** (list of **{id, threadId}**).
- **Exception:** Wrap in **RuntimeError** so callers see a clear failure; **from e** preserves the cause.
- **return:** Extract **id** from each item in **result["messages"]**; if **messages** is missing, use **[]**.

---

## 7. `fetch_recent_inbox` (lines 104–124)

**Purpose:** Fetch recent INBOX messages and return them as a list of **email_input** dicts. Optionally use only unread messages. Used by the Gmail watcher to get a batch of emails to pass into the graph (e.g. one at a time with **email_input**).

```python
def fetch_recent_inbox(
    service=None,
    max_results: int = 20,
    unread_only: bool = False,
) -> list[dict]:
    """
    Fetch recent INBOX messages and return them as email_input dicts.

    Use cases: Gmail watcher calls this to get new emails to pass into the graph.
    """
```

- **service:** Gmail API v1 service. If **None**, call **get_gmail_service()** so the watcher can call **fetch_recent_inbox()** with no args.
- **max_results, unread_only:** Passed through to **list_inbox_message_ids**.
- **Returns:** List of **email_input**-shaped dicts (from, to, subject, body, id). Order follows the list of ids (often newest first).

```python
    if service is None:
        service = get_gmail_service()
    ids = list_inbox_message_ids(service, max_results=max_results, unread_only=unread_only)
    out = []
    for mid in ids:
        email_input = get_message_as_email_input(service, mid)
        if email_input:
            out.append(email_input)
    return out
```

- **service:** Lazy-init if not provided.
- **ids:** Get INBOX message ids (recent or unread, limited by **max_results**).
- **Loop:** For each id, **get_message_as_email_input(service, mid)**. If it returns a dict (success), append to **out**. If it returns **None** (fetch failed), skip that message so one bad message doesn’t break the batch.
- **return out:** List of **email_input** dicts ready to be passed to the graph as **{"email_input": ...}** (typically one email per invocation for triage + response).

---

## 8. Flow summary

1. **Gmail watcher** (e.g. **watch_gmail.py**) calls **fetch_recent_inbox()** or **list_inbox_message_ids()** plus **get_message_as_email_input()** to get **email_input** dicts from real Gmail.
2. **list_inbox_message_ids** uses **messages.list** with INBOX, optional **is:unread** and **query**, and **max_results**.
3. **get_message_as_email_input** uses **messages.get** (format=full), **_decode_body** for body text, **_header** for From/To/Subject, and returns **{from, to, subject, body, id}** (body/snippet truncated to 8000).
4. **fetch_recent_inbox** composes: list ids → for each id, get **email_input** → return list of dicts. Watcher then invokes the graph with **input={"email_input": one_of_these}** so **input_router** and triage run on real inbox messages.
5. **input_router** normalizes these dicts (they already have from/to/subject/body/id) and sets **_source** to **"gmail"** so triage knows they’re incoming Gmail messages.

---

## 9. Related files

- **Auth:** `src/email_assistant/tools/gmail/auth.py` (**get_gmail_service**, **gmail.readonly** scope).
- **Input router:** `src/email_assistant/nodes/input_router.py` (**_normalize_email_input** accepts flat dict with from/to/subject/body/id; sets **_source** for Gmail).
- **Watcher:** Scripts that use this module (e.g. **watch_gmail.py**) to poll or watch Gmail and invoke the graph with **email_input**).
- **StateInput / email_input:** `src/email_assistant/schemas.py` (**StateInput** includes **email_input**).

For auth and scopes, see **docs/code-explanations/tools_gmail_auth.md**. For how **email_input** is normalized and used, see **docs/code-explanations/nodes_input_router.md**.
