# Explanation: `db/persist_messages.py`

Detailed walkthrough of **persist_messages**: writing conversation messages to **email_assistant.chats** and **email_assistant.messages** so chat history is queryable in Postgres (Phase 3). Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–7)

```python
"""
Persist conversation messages to email_assistant.chats and email_assistant.messages.

Use cases: after each graph run, sync state["messages"] to Postgres for queryable
chat history (Phase 3). Uses thread_id as stable chat_id (UUID5) and user_id from config/env.
"""
```

- **Line 2:** This module **persists** conversation messages to the **email_assistant** schema: **chats** (one row per thread) and **messages** (one row per message). Tables are created by **migrations/001_email_assistant_tables.sql** (or equivalent).
- **Lines 4–5:** **Use cases:** After each graph run, **state["messages"]** is synced to Postgres so chat history can be queried (e.g. for UI, analytics, or loading prior context). Phase 3 introduces this persistence.
- **Line 5:** **thread_id** (from LangGraph config) is turned into a stable **chat_id** (UUID5) so the same thread always maps to the same chat. **user_id** comes from config or env (e.g. **get_config()["configurable"]["user_id"]** or **USER_ID**).

---

## 2. Imports (lines 9–15)

```python
import json
import uuid
from typing import Any
```

- **json:** **metadata** (e.g. **additional_kwargs** from messages) is stored as JSONB; we use **json.dumps(metadata)** for the insert.
- **uuid:** **uuid5** is used to derive a stable **chat_id** from **thread_id** (same thread_id ⇒ same chat_id) and to normalize **user_id** to a UUID when it’s not already valid.
- **Any:** Type hint for **metadata** dict values (mixed types from message kwargs).

```python
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from psycopg import Connection
from psycopg.rows import dict_row
```

- **BaseMessage, HumanMessage, AIMessage, SystemMessage:** LangChain message types. We map them to **role** (user, assistant, system, tool) and extract **content** and optional **metadata** for the DB.
- **Connection:** **psycopg** connection. We use **Connection.connect(...)** as a context manager so the connection is closed on exit. **autocommit=True** and **row_factory=dict_row** (same pattern as other db modules; **prepare_threshold** is not set here, so default is used).
- **dict_row:** Rows as dicts (used if we run queries that return rows; the current code only does inserts/delete).

---

## 3. `THREAD_NAMESPACE` (lines 17–18)

```python
# Stable namespace for deriving chat_id from thread_id (string) so same thread_id => same chat_id.
THREAD_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "email_assistant.chat_id")
```

- **Purpose:** UUID5 namespace for **thread_id_to_chat_id**. **uuid5(namespace, name)** is deterministic: the same **name** (thread_id string) always produces the same UUID. So the same LangGraph **thread_id** always maps to the same **chat_id** in **email_assistant.chats**, keeping one chat row per thread.
- **uuid.NAMESPACE_DNS:** Standard UUID namespace; we combine it with the string **"email_assistant.chat_id"** to get a project-specific namespace so our chat_ids don’t collide with other UUID5 usages.

---

## 4. `_message_role` (lines 21–29)

```python
def _message_role(msg: BaseMessage) -> str:
    """Map LangChain message type to email_assistant.messages.role."""
    if isinstance(msg, HumanMessage):
        return "user"
    if isinstance(msg, AIMessage):
        return "assistant"
    if isinstance(msg, SystemMessage):
        return "system"
    return "tool"
```

- **Purpose:** Map a LangChain **BaseMessage** to the **role** value stored in **email_assistant.messages** (user, assistant, system, tool). The DB schema expects a single **role** column; we don’t store the full message type.
- **HumanMessage → "user", AIMessage → "assistant", SystemMessage → "system":** Standard mapping. Any other type (e.g. **ToolMessage**) is treated as **"tool"** so we don’t fail on unknown message types.

---

## 5. `_message_content` (lines 32–44)

```python
def _message_content(msg: BaseMessage) -> str | None:
    """Extract content for DB; prefer string content."""
    content = getattr(msg, "content", None)
    if isinstance(content, str):
        return content
```

- **Purpose:** Extract a string (or None) for the **content** column. LangChain messages can have **content** as a string or a list (e.g. multimodal). We prefer a single string for the DB.
- **content = getattr(msg, "content", None):** Safe access to **content** (may be missing on some message types).
- **if isinstance(content, str): return content:** Most common case; return as-is.

```python
    if isinstance(content, list):
        # Multimodal: could join text parts; for Phase 3 store repr or first text
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                return part.get("text", "")
        return str(content)[:10000]
    return str(content) if content is not None else None
```

- **List content (multimodal):** If **content** is a list (e.g. blocks with type and text), look for a part with **type == "text"** and return its **text**. If none found, store **str(content)** truncated to 10000 chars so we don’t blow the column size.
- **Other:** If **content** is not str or list, use **str(content)** or **None** so the DB always gets a string or NULL.

---

## 6. `thread_id_to_chat_id` (lines 47–49)

```python
def thread_id_to_chat_id(thread_id: str) -> uuid.UUID:
    """Return a stable UUID for the chat from thread_id (for DB chats.chat_id)."""
    return uuid.uuid5(THREAD_NAMESPACE, thread_id)
```

- **Purpose:** Convert a LangGraph **thread_id** (string) to a stable **UUID** for **email_assistant.chats.chat_id**. Same **thread_id** always gives the same **chat_id**, so one thread maps to one chat row and we can **DELETE ... WHERE chat_id = %s** then insert the current messages to “sync” the conversation.
- **uuid.uuid5(THREAD_NAMESPACE, thread_id):** Deterministic UUID from the namespace and thread_id string. Safe for use as a primary key and stable across runs.

---

## 7. `persist_messages` (lines 52–108)

**Purpose:** Ensure the user and chat exist in **email_assistant.users** and **email_assistant.chats**, then replace all messages for that chat with the current **messages** list. Called from **_persist_messages_node** in **simple_agent.py** after the response subgraph finishes; **thread_id** and **user_id** come from LangGraph config (or env). Requires **migrations/001_email_assistant_tables.sql** to have been run.

```python
def persist_messages(
    conn_string: str,
    thread_id: str,
    user_id: str,
    messages: list[BaseMessage],
) -> None:
    """
    Ensure user and chat exist, then insert all messages into email_assistant.messages.

    Use cases: call after graph.invoke() with result["messages"]; thread_id and user_id
    from config. Requires migrations/001_email_assistant_tables.sql to have been run.
    """
```

- **conn_string:** Database URL (e.g. from **DATABASE_URL**). Passed from the node that reads env and config.
- **thread_id, user_id:** From LangGraph run config (e.g. **configurable["thread_id"]**, **configurable["user_id"]**), or env fallbacks. Used to resolve **chat_id** and to associate messages with a user and chat.
- **messages:** Full list of messages for this run (state["messages"]). We replace the DB’s messages for this chat with this list so the DB reflects the current conversation after each run.
- **Returns:** None. Side effect only: upsert user, upsert chat, delete existing messages for the chat, insert all **messages**.

```python
    chat_id = thread_id_to_chat_id(thread_id)
    try:
        u = uuid.UUID(user_id)
    except (ValueError, TypeError):
        u = uuid.uuid5(THREAD_NAMESPACE, f"user_{user_id}")
```

- **chat_id:** Stable UUID from **thread_id** for **chats.chat_id** and **messages.chat_id**.
- **u:** **user_id** as a UUID. If **user_id** is already a valid UUID string, use it. Otherwise (e.g. opaque string like "default-user") derive a stable UUID with **uuid5(THREAD_NAMESPACE, f"user_{user_id}")** so the same user_id string always maps to the same **users.user_id**.

```python
    with Connection.connect(conn_string, autocommit=True, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
```

- **Connection.connect(...):** Open a connection; **with** ensures it is closed. **autocommit=True** so each execute commits immediately. **row_factory=dict_row** for consistency with other db code. No **search_path** is set; table names are schema-qualified (**email_assistant.users**, etc.).
- **conn.cursor():** Cursor for executing SQL.

```python
            # Ensure user exists
            cur.execute(
                """
                INSERT INTO email_assistant.users (user_id, updated_at)
                VALUES (%s, now())
                ON CONFLICT (user_id) DO UPDATE SET updated_at = now()
                """,
                (u,),
            )
```

- **Upsert user:** Insert a row into **email_assistant.users** with **user_id** and **updated_at**. If **user_id** already exists (**ON CONFLICT (user_id)**), only update **updated_at**. So every run ensures the user row exists without failing on duplicate key.

```python
            # Ensure chat exists
            cur.execute(
                """
                INSERT INTO email_assistant.chats (chat_id, user_id, updated_at)
                VALUES (%s, %s, now())
                ON CONFLICT (chat_id) DO UPDATE SET updated_at = now()
                """,
                (chat_id, u),
            )
```

- **Upsert chat:** Insert a row into **email_assistant.chats** with **chat_id**, **user_id**, **updated_at**. If **chat_id** already exists, only update **updated_at**. So the chat row exists for this thread and is linked to the user.

```python
            # Replace messages for this chat (sync full conversation; avoids duplicates when graph runs each turn)
            cur.execute(
                "DELETE FROM email_assistant.messages WHERE chat_id = %s",
                (chat_id,),
            )
```

- **Delete existing messages:** Remove all messages for this **chat_id**. We then insert the current **messages** list so the DB holds exactly the conversation after this run. This “replace” strategy avoids duplicate messages when the graph is invoked multiple times for the same thread (each run overwrites with the full list).

```python
            # Insert current messages
            for msg in messages:
                role = _message_role(msg)
                content = _message_content(msg)
                metadata: dict[str, Any] = {}
                if hasattr(msg, "additional_kwargs") and msg.additional_kwargs:
                    metadata = dict(msg.additional_kwargs)
                cur.execute(
                    """
                    INSERT INTO email_assistant.messages (chat_id, user_id, role, content, metadata)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    """,
                    (chat_id, u, role, content, json.dumps(metadata)),
                )
```

- **Loop:** For each message in **messages**, compute **role** (user/assistant/system/tool) and **content** (string or None) with **_message_role** and **_message_content**.
- **metadata:** If the message has **additional_kwargs**, store them as JSON in the **metadata** column (e.g. tool_call ids, custom fields). Otherwise store **{}**. **json.dumps(metadata)** produces a string; **%s::jsonb** casts it to JSONB in Postgres.
- **INSERT:** One row per message with **chat_id**, **user_id**, **role**, **content**, **metadata**. Order of rows follows **messages** order (message order is preserved by insert order; if the table has an ordering column like **created_at** or **sequence**, that would determine display order unless you add an explicit position column).

---

## 8. Flow summary

1. **_persist_messages_node** (in **simple_agent.py**) runs after the chat/tools loop. It reads **DATABASE_URL**, **thread_id** and **user_id** from **get_config()** (or env), and **state["messages"]**. If **DATABASE_URL** and **messages** are set, it calls **persist_messages(conn_string, thread_id, user_id, list(state["messages"]))**.
2. **persist_messages** derives **chat_id** from **thread_id** and normalizes **user_id** to a UUID. It opens a connection and in one transaction (autocommit per statement): upserts **email_assistant.users**, upserts **email_assistant.chats**, deletes all **email_assistant.messages** for that **chat_id**, then inserts one row per message with role, content, and metadata.
3. The same **thread_id** always yields the same **chat_id**, so repeated runs for the same thread overwrite that chat’s messages with the latest conversation. Chat history in the DB is therefore the state after the last run for that thread.
4. Tables **email_assistant.users**, **email_assistant.chats**, **email_assistant.messages** must exist (e.g. from **migrations/001_email_assistant_tables.sql**).

---

## 9. Related files

- **Caller:** `src/email_assistant/simple_agent.py` (**_persist_messages_node** calls **persist_messages** with conn_string, thread_id, user_id, messages from state and config).
- **Migrations:** **migrations/001_email_assistant_tables.sql** (or equivalent) defines **email_assistant.users**, **email_assistant.chats**, **email_assistant.messages**.
- **Config:** **thread_id** and **user_id** come from **get_config()["configurable"]** when the graph is invoked (e.g. CLI or Studio); see **CONFIGURATION.md** or run scripts.

For the node that calls this, see **docs/code-explanations/simple_agent.md**. For database schema, see **docs/DATABASE.md** or **docs/guide/05_DATABASE_AND_PERSISTENCE.md** if present.
