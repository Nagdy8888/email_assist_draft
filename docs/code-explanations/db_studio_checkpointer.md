# Explanation: `db/studio_checkpointer.py`

Detailed walkthrough of the **async checkpointer** used by LangGraph Studio (`langgraph dev`): it yields an **AsyncPostgresSaver** with **search_path=email_assistant** and runs **setup()** so checkpoint tables exist. Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–9)

```python
"""
Async checkpointer for LangGraph Studio (langgraph dev).

Use cases: yield an AsyncPostgresSaver with search_path=email_assistant so Studio
uses the same Supabase Postgres as CLI scripts. Referenced by langgraph.json
checkpointer.path. Run setup() on entry so checkpoint tables exist in email_assistant.
Uses a single connection with prepare_threshold=None (Supabase-friendly); the server
keeps the context open for the duration of the server so checkpoints persist.
"""
```

- **Line 2:** This module provides an **async** checkpointer for **LangGraph Studio** (the dev server started with **langgraph dev**). Studio runs the graph in an async context and needs an async-compatible checkpointer.
- **Lines 4–5:** **Use cases:** Yield an **AsyncPostgresSaver** that uses **search_path=email_assistant** so Studio writes checkpoints to the same schema (and typically the same Supabase Postgres) as CLI scripts. The checkpointer is **referenced by langgraph.json** (e.g. **checkpointer.path** pointing to this module’s **generate_checkpointer**).
- **Line 6:** **setup()** is called on entry so the checkpoint tables are created in **email_assistant** if they don’t exist (unlike **db/checkpointer.py**, which does not call **setup()** and expects **scripts/setup_db.py** to have run first).
- **Lines 7–8:** The connection uses **prepare_threshold=None** to avoid prepared-statement issues with Supabase/pooled backends. The Studio server keeps the checkpointer context open for its lifetime, so the connection stays open and checkpoints persist across requests.

---

## 2. Imports (lines 11–16)

```python
import contextlib
import os
```

- **contextlib:** Used for **@contextlib.asynccontextmanager** so **generate_checkpointer** is an **async** context manager (entry and exit are async).
- **os:** **os.getenv("DATABASE_URL")** to read the database URL.

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row
```

- **AsyncPostgresSaver:** LangGraph’s async PostgreSQL checkpointer. Same role as **PostgresSaver** but with async methods (**await saver.setup()**, etc.). Used by the LangGraph dev server when serving the graph with a checkpointer.
- **AsyncConnection:** **psycopg**’s async connection. **AsyncConnection.connect(...)** is awaited to open the connection; **conn.cursor()** is used as an async context manager; **conn.close()** is awaited in **finally**.
- **dict_row:** Row factory so query results are dict-like (same as in **db/checkpointer.py**).

---

## 3. `generate_checkpointer` (lines 19–43)

**Purpose:** Async context manager that yields an **AsyncPostgresSaver** for **DATABASE_URL**, with **search_path=email_assistant**, and runs **await saver.setup()** so checkpoint tables exist. The LangGraph Studio server invokes this (via **langgraph.json**) and keeps the context open for the server’s lifetime so the same connection and checkpointer are used for all runs. Connection options match **db/checkpointer.py** (autocommit, **prepare_threshold=None**) for Supabase compatibility.

```python
@contextlib.asynccontextmanager
async def generate_checkpointer():
    """
    Yield an AsyncPostgresSaver for DATABASE_URL with search_path=email_assistant.

    Use cases: LangGraph Studio injects this when langgraph.json has
    "checkpointer": {"path": "...:generate_checkpointer"}. The server keeps this
    context open for its lifetime, so the connection stays open and checkpoints
    are written to email_assistant schema. Uses prepare_threshold=None for
    Supabase/pooled backends.
    """
```

- **@contextlib.asynccontextmanager:** Makes the function an **async** context manager. The caller uses **async with generate_checkpointer() as saver:** (or the server’s equivalent); the code before **yield** runs on entry, the code after **yield** runs on exit.
- **Docstring:** Studio injects the checkpointer when **langgraph.json** specifies **checkpointer.path** (e.g. **"email_assistant.db.studio_checkpointer:generate_checkpointer"**). The server keeps this context open for its lifetime, so the connection and saver are long-lived and checkpoints persist. **prepare_threshold=None** is for Supabase and other pooled backends.

```python
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is required for Studio checkpointer. Set it in .env and restart langgraph dev.")
```

- **url:** Database connection string (e.g. Supabase Postgres). If missing, raise a clear error so the user knows to set **DATABASE_URL** in **.env** and restart **langgraph dev**.

```python
    conn = await AsyncConnection.connect(
        url, autocommit=True, prepare_threshold=None, row_factory=dict_row
    )
```

- **AsyncConnection.connect(...):** Open an async connection. **await** is required because connect is async.
- **autocommit=True:** Each statement commits immediately; no explicit **commit()**.
- **prepare_threshold=None:** Disable prepared statements to avoid **DuplicatePreparedStatement** or name clashes with Supabase/pooled connections (same as in **db/checkpointer.py**).
- **row_factory=dict_row:** Rows as dicts.

```python
    try:
        async with conn.cursor() as cur:
            await cur.execute("SET search_path TO email_assistant")
        saver = AsyncPostgresSaver(conn)
        await saver.setup()
        yield saver
    finally:
        await conn.close()
```

- **async with conn.cursor() as cur:** Open an async cursor, run **SET search_path TO email_assistant** so all subsequent operations (including **saver.setup()** and checkpoint reads/writes) use the **email_assistant** schema.
- **saver = AsyncPostgresSaver(conn):** Create the async checkpointer with this connection.
- **await saver.setup():** Create the checkpoint tables in **email_assistant** if they don’t exist. So Studio can start without a separate **scripts/setup_db.py** run; the first time the server runs, tables are created. (If you use a migration like **002_checkpoint_created_at.sql**, that may still need to be run separately or added to setup logic.)
- **yield saver:** The Studio server receives this **AsyncPostgresSaver** and uses it for all graph runs (thread state, interrupt/resume). The context stays open until the server shuts down.
- **finally: await conn.close():** When the context exits (e.g. server shutdown), close the connection.

---

## 4. Flow summary

1. **langgraph.json** (or Studio config) points the checkpointer to this module, e.g. **"checkpointer": {"path": "email_assistant.db.studio_checkpointer:generate_checkpointer"}**.
2. When the LangGraph dev server starts, it invokes **generate_checkpointer()** and enters the async context. It gets **DATABASE_URL** from the environment (often loaded from **.env** by the server).
3. The server opens an **AsyncConnection** with **search_path=email_assistant** and **prepare_threshold=None**, creates **AsyncPostgresSaver(conn)**, and calls **await saver.setup()** so checkpoint tables exist.
4. The server yields **saver** and keeps the context open. Every graph run (and resume after **interrupt()**) uses this same checkpointer and connection. Threads and checkpoints persist in the **email_assistant** schema, same as CLI when using **postgres_checkpointer()**.
5. On server shutdown, the context exits and **await conn.close()** runs.

---

## 5. Related files

- **langgraph.json:** References **generate_checkpointer** (e.g. **checkpointer.path**). The dev server loads this to know which checkpointer to use when serving the graph.
- **CLI checkpointer:** `src/email_assistant/db/checkpointer.py` (**postgres_checkpointer** is sync and does not call **setup()**; **studio_checkpointer** is async and does call **setup()**).
- **Graph entry:** `src/email_assistant/email_assistant_hitl_memory_gmail.py` exports **email_assistant = build_email_assistant_graph()** with no checkpointer; the Studio server injects the checkpointer from config (this module).
- **HITL:** **interrupt()** in **triage_interrupt_handler** requires a checkpointer; Studio uses this async saver so state is persisted and can be resumed.

For the sync Postgres checkpointer used by CLI, see **docs/code-explanations/db_checkpointer.md**. For how the graph is compiled and where the checkpointer is injected, see **docs/code-explanations/email_assistant_hitl_memory_gmail.md**.
