# Explanation: `db/store.py`

Detailed walkthrough of the **store** module: wrapper for LangGraph’s **PostgresStore** used for memory (Phase 6). It provides a context manager **postgres_store()** and a **setup_store()** function to create the store table in the **email_assistant** schema. Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–7)

```python
"""
Store for memory: PostgresStore (LangGraph built-in) from DATABASE_URL.

Use cases: back get_memory/update_memory with LangGraph's store table; pass into
graph compile(store=...) when using memory (Phase 6). For Phase 3 the simple agent
does not use the store; setup_store() is called from scripts/setup_db.py.
"""
```

- **Line 2:** This module provides the **store** used for **memory**: LangGraph’s **PostgresStore**, built from **DATABASE_URL**. The store holds key-value–style data (e.g. user preferences, memory entries) that nodes can read/write via **get_memory** / **update_memory** or the graph’s store API.
- **Lines 4–5:** **Use cases:** The store backs **get_memory** / **update_memory** (Phase 6 memory features) using LangGraph’s store table. When using memory, the graph is compiled with **compile(store=...)** and this **PostgresStore** is passed in. For Phase 3 (simple agent without memory), the store is not used.
- **Line 6:** **setup_store()** is intended to be run once (e.g. from **scripts/setup_db.py**) to create the store table; the **postgres_store()** context manager does not call **setup()** itself (similar to **postgres_checkpointer()**).

---

## 2. Imports (lines 9–14)

```python
import os
from contextlib import contextmanager
from typing import Iterator
```

- **os:** **os.getenv("DATABASE_URL")** to read the database URL.
- **contextmanager:** Decorator for **postgres_store()** so it can be used as **with postgres_store() as store: ...** and the connection is closed on exit.
- **Iterator:** Type hint for the context manager’s yield type (**Iterator[PostgresStore]**).

```python
from langgraph.store.postgres import PostgresStore
from psycopg import Connection
from psycopg.rows import dict_row
```

- **PostgresStore:** LangGraph’s PostgreSQL-backed store. It persists key-value (or namespace/key) data so the graph can read and update memory across runs and threads. Used when the graph is compiled with **store=...** (Phase 6 memory).
- **Connection:** **psycopg** sync connection. Same pattern as **db/checkpointer.py**: **Connection.connect(...)** with **autocommit=True**, **prepare_threshold=None**, **row_factory=dict_row** for Supabase/pooled backends.
- **dict_row:** Rows as dicts.

---

## 3. `postgres_store` (lines 17–37)

**Purpose:** Context manager that opens a PostgreSQL connection with **search_path=email_assistant**, yields a **PostgresStore** that uses that connection, and closes the connection on exit. Requires **DATABASE_URL**. Does **not** run **setup()**; the store table should be created beforehand (e.g. via **setup_store()** from **scripts/setup_db.py**).

```python
@contextmanager
def postgres_store() -> Iterator[PostgresStore]:
    """
    Yield a PostgresStore for DATABASE_URL in the email_assistant schema.

    Use cases: compile graph with store=... when using memory; or call setup()
    inside this context to create the store table. Uses prepare_threshold=None
    to avoid DuplicatePreparedStatement with Supabase/pooled connections.
    """
```

- **@contextmanager:** Makes the function a context manager; the caller uses **with postgres_store() as store:** and **store** is the **PostgresStore**.
- **Yields:** **PostgresStore** so the caller can pass it to **graph.compile(store=store)** when using memory (Phase 6).
- **Docstring:** Table creation can be done by calling **setup()** inside this context, or by running **setup_store()** separately. **prepare_threshold=None** avoids prepared-statement issues with Supabase/pooled connections.

```python
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is required for postgres store")
```

- **url:** Database connection string. If missing, raise so the caller gets a clear error.

```python
    conn = Connection.connect(
        url, autocommit=True, prepare_threshold=None, row_factory=dict_row
    )
```

- **Connection.connect(...):** Same options as in **db/checkpointer.py**: **autocommit=True**, **prepare_threshold=None** (Supabase-friendly), **row_factory=dict_row**.

```python
    try:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO email_assistant")
        yield PostgresStore(conn)
    finally:
        conn.close()
```

- **SET search_path TO email_assistant:** All store table operations use the **email_assistant** schema so the store table lives alongside checkpoint and messages tables.
- **yield PostgresStore(conn):** **PostgresStore** uses this connection for all store reads/writes. The caller holds the yielded store for the duration of the **with** block (e.g. to compile the graph with **store=store**).
- **finally: conn.close():** Connection is always closed when the context exits.

---

## 4. `setup_store` (lines 40–61)

**Purpose:** Create the LangGraph store table in Postgres (in the **email_assistant** schema). Uses a dedicated connection with **search_path=email_assistant** and **prepare_threshold=None**. Idempotent if **PostgresStore.setup()** is implemented to create tables only when they don’t exist. Intended to be run once (e.g. from **scripts/setup_db.py**) before using the store.

```python
def setup_store() -> None:
    """
    Create the LangGraph store table in Postgres (idempotent).

    Use cases: run once before using the store, e.g. from scripts/setup_db.py.
    Uses a dedicated connection with prepare_threshold=None to avoid
    DuplicatePreparedStatement when using Supabase or other pooled backends.
    """
```

- **Returns:** None. Side effect is creating the store table(s) via **store.setup()**.
- **Docstring:** Run once before using the store (e.g. from **scripts/setup_db.py**). Uses its own connection and **prepare_threshold=None** for Supabase/pooled backends.

```python
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is required for postgres store")
    conn = Connection.connect(
        url, autocommit=True, prepare_threshold=None, row_factory=dict_row
    )
```

- Same as **postgres_store()**: get **DATABASE_URL**, raise if missing, open connection with the same options.

```python
    try:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO email_assistant")
        store = PostgresStore(conn)
        store.setup()
    finally:
        conn.close()
```

- **SET search_path TO email_assistant:** So **store.setup()** creates the table(s) in **email_assistant**.
- **store = PostgresStore(conn); store.setup():** **PostgresStore.setup()** creates the store table (and any required schema). Typically idempotent (e.g. CREATE TABLE IF NOT EXISTS).
- **finally: conn.close():** Always close the connection. **setup_store()** does not yield the store; it only creates the table and exits.

---

## 5. Flow summary

1. **Phase 3 (simple agent):** The graph is compiled without a store; **db/store.py** is not used at runtime. **setup_store()** can still be run from **scripts/setup_db.py** to create the table for later use.
2. **Phase 6 (memory):** When the graph uses memory (get_memory / update_memory), the app compiles the graph with **store=...**. The caller uses **with postgres_store() as store:** and passes **store** to **compile(store=store)**. The store table must already exist (created by **setup_store()** or by calling **store.setup()** inside **postgres_store()** context).
3. **setup_store():** Run once (e.g. in **scripts/setup_db.py**) to create the store table in **email_assistant**. Uses a dedicated connection; same **search_path** and **prepare_threshold=None** as **postgres_store()**.
4. **postgres_store():** Same connection pattern as **postgres_checkpointer()**: single connection, **search_path**, yield the LangGraph object, close in **finally**.

---

## 6. Related files

- **Checkpointer:** `src/email_assistant/db/checkpointer.py` (same connection pattern: **postgres_checkpointer()**, **setup** run separately).
- **Setup script:** **scripts/setup_db.py** (typically calls **setup_store()** along with checkpoint setup and migrations).
- **Graph / memory:** When Phase 6 memory is wired, the graph is compiled with **store=...** and nodes use the store for get_memory/update_memory. The current **email_assistant_hitl_memory_gmail.py** does not pass a store; memory integration would add it here or in a variant entry point.
- **DATABASE_URL:** Same env var as checkpointer and persist_messages; see **docs/CONFIGURATION.md** or **docs/guide/06_CONFIGURATION.md**.

For the sync Postgres checkpointer and setup pattern, see **docs/code-explanations/db_checkpointer.md**. For database and schema overview, see **docs/DATABASE.md** or **docs/guide/05_DATABASE_AND_PERSISTENCE.md** if present.
