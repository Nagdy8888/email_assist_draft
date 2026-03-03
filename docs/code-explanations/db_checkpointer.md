# Explanation: `db/checkpointer.py`

Detailed walkthrough of the **checkpointer** module: wrapper and config for the LangGraph checkpointer. It provides a Postgres checkpointer (via **postgres_checkpointer()**) when **DATABASE_URL** is set, and a helper to run the checkpoint **created_at** migration. Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–8)

```python
"""
Wrapper/config for PostgresSaver (LangGraph checkpointer).

Use cases: create checkpointer from DATABASE_URL; call setup() for checkpoint tables;
pass into graph compile(checkpointer=...). Use postgres_checkpointer() as a context
manager when DATABASE_URL is set; otherwise use MemorySaver in the caller.
Checkpoint tables are created in the email_assistant schema via search_path.
"""
```

- **Line 2:** This module is a **wrapper/config** for **PostgresSaver** (LangGraph’s PostgreSQL checkpointer). It builds a checkpointer from **DATABASE_URL** and configures it to use the **email_assistant** schema.
- **Lines 4–5:** **Use cases:** Create a checkpointer from **DATABASE_URL**; run **setup()** (e.g. via **scripts/setup_db.py**) to create checkpoint tables; pass the checkpointer into **graph.compile(checkpointer=...)**. When **DATABASE_URL** is set, use **postgres_checkpointer()** as a context manager; when it’s not set, the caller uses **MemorySaver** (e.g. via **get_checkpointer()**).
- **Line 6:** Checkpoint tables live in the **email_assistant** schema; the connection **search_path** is set to **email_assistant** so table names resolve to that schema.

---

## 2. Imports (lines 10–18)

```python
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional
```

- **os:** Read **DATABASE_URL** with **os.getenv()**.
- **contextmanager:** Decorator for **postgres_checkpointer()** so it can be used as **with postgres_checkpointer() as cp: ...** and the connection is closed in **finally**.
- **Path:** Resolve the path to **migrations/002_checkpoint_created_at.sql** in **run_checkpoint_created_at_migration**.
- **Iterator, Optional:** Type hints for the context manager yield type and the optional **migration_path** argument.

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
```

- **MemorySaver:** In-memory checkpointer (no persistence). Returned by **get_checkpointer()** when **DATABASE_URL** is not set; good for local/dev or single-run scripts.
- **PostgresSaver:** LangGraph’s PostgreSQL checkpointer. Persists thread state and checkpoints so the graph can resume after **interrupt()** (e.g. HITL) and so threads persist across restarts. Created inside **postgres_checkpointer()** with a single connection.

```python
from psycopg import Connection
from psycopg.rows import dict_row
```

- **Connection:** **psycopg** (PostgreSQL adapter) connection. We use **Connection.connect(...)** to open a connection with **autocommit=True**, **prepare_threshold=None**, and **row_factory=dict_row** so we avoid prepared-statement issues with pooled connections (e.g. Supabase) and get dict-like rows if needed.
- **dict_row:** Row factory that returns rows as dicts (used for consistency; PostgresSaver may use the connection for queries).

---

## 3. `postgres_checkpointer` (lines 21–38)

**Purpose:** Context manager that opens a PostgreSQL connection with **search_path=email_assistant**, yields a **PostgresSaver** that uses that connection, and closes the connection on exit. Requires **DATABASE_URL**. Does **not** run **setup()**; run **scripts/setup_db.py** once to create checkpoint tables.

```python
@contextmanager
def postgres_checkpointer() -> Iterator[PostgresSaver]:
    """
    Yield a PostgresSaver for DATABASE_URL with search_path=email_assistant.
    Does not run setup(); run scripts/setup_db.py once to create checkpoint tables
    and avoid DuplicatePreparedStatement when using pooled connections (e.g. Supabase).
    """
```

- **@contextmanager:** Makes the function a context manager; the code before **yield** runs on entry, the code after **yield** runs on exit (in a **finally**-like way). The caller uses **with postgres_checkpointer() as cp: ...** and **cp** is the **PostgresSaver**.
- **Yield:** Yields a **PostgresSaver** so the caller can pass it to **builder.compile(checkpointer=cp)**.
- **Docstring:** **setup()** is not called here; run **scripts/setup_db.py** once to create the checkpoint tables. Creating tables here with pooled connections (e.g. Supabase) can cause **DuplicatePreparedStatement** issues, so table creation is done separately.

```python
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is required for postgres checkpointer")
```

- **url:** Database connection string (e.g. Postgres or Supabase). If missing, raise so the caller doesn’t get a confusing connection error later.

```python
    conn = Connection.connect(
        url, autocommit=True, prepare_threshold=None, row_factory=dict_row
    )
```

- **Connection.connect(url, ...):** Open a single connection to the database.
- **autocommit=True:** Each statement commits immediately; no explicit **commit()** needed. Suitable for short-lived scripts and for PostgresSaver’s operations.
- **prepare_threshold=None:** Disable prepared statements. With connection pools (e.g. Supabase), reusing connections with prepared statements can lead to **DuplicatePreparedStatement** or statement-name clashes; **None** avoids that.
- **row_factory=dict_row:** Rows returned as dicts (useful if any code fetches rows from this connection).

```python
    try:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO email_assistant")
        yield PostgresSaver(conn)
    finally:
        conn.close()
```

- **SET search_path TO email_assistant:** So all unqualified table names (e.g. **checkpoints**, **checkpoint_writes**) refer to tables in the **email_assistant** schema. PostgresSaver then creates/uses tables in that schema.
- **yield PostgresSaver(conn):** PostgresSaver uses this connection for all checkpoint reads/writes. The caller holds the yielded **PostgresSaver** for the duration of the **with** block.
- **finally: conn.close():** When the block exits (normally or by exception), close the connection so it isn’t left open.

---

## 4. `run_checkpoint_created_at_migration` (lines 41–67)

**Purpose:** Run the migration that adds **created_at** to the checkpoint tables (e.g. **migrations/002_checkpoint_created_at.sql**). Opens its own connection with **search_path=email_assistant**, executes the SQL file, then closes. Idempotent if the migration is written to be safe to run multiple times. Intended to be called from **scripts/setup_db.py** after **cp.setup()**.

```python
def run_checkpoint_created_at_migration(migration_path: Optional[Path] = None) -> None:
    """
    Run migrations/002_checkpoint_created_at.sql to add created_at to checkpoint tables.

    Use cases: call from scripts/setup_db.py after cp.setup(). Opens a connection
    with search_path=email_assistant, executes the SQL, closes. Idempotent.
    """
```

- **migration_path:** Path to the SQL file. If **None**, defaults to **migrations/002_checkpoint_created_at.sql** relative to the project root (computed from **__file__**).
- **Returns:** None. Side effect is running the SQL (e.g. **ALTER TABLE ... ADD COLUMN created_at ...**).
- **Docstring:** Typically called from **scripts/setup_db.py** after **PostgresSaver.setup()** has created the base checkpoint tables. Uses a dedicated connection with **search_path=email_assistant**. Idempotent if the migration uses **IF NOT EXISTS** or similar.

```python
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is required")
    if migration_path is None:
        migration_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "migrations"
            / "002_checkpoint_created_at.sql"
        )
    sql = migration_path.read_text()
```

- **url:** Same as in **postgres_checkpointer**; required to connect.
- **migration_path default:** **__file__** is **.../src/email_assistant/db/checkpointer.py**. **parent** x4: db → email_assistant → src → **project root**. So **migration_path** = **project_root / "migrations" / "002_checkpoint_created_at.sql"**.
- **sql:** Read the entire migration file as text so we can **cur.execute(sql)**.

```python
    conn = Connection.connect(
        url, autocommit=True, prepare_threshold=None, row_factory=dict_row
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO email_assistant")
            cur.execute(sql)
    finally:
        conn.close()
```

- **Connection:** Same options as in **postgres_checkpointer** (autocommit, no prepared statements, dict_row).
- **SET search_path TO email_assistant:** So the migration’s table names (e.g. **checkpoints**) refer to the **email_assistant** schema.
- **cur.execute(sql):** Run the migration (e.g. add **created_at** columns). The migration file should be written so it’s safe to run multiple times (e.g. **ADD COLUMN IF NOT EXISTS** or equivalent).
- **finally: conn.close():** Always close the connection.

---

## 5. `get_checkpointer` (lines 70–80)

**Purpose:** Return a checkpointer suitable for **graph.compile(checkpointer=...)**. When **DATABASE_URL** is set, return the **postgres_checkpointer()** context manager (caller must use **with get_checkpointer() as cp:** and then **compile(checkpointer=cp)**). When **DATABASE_URL** is not set, return a **MemorySaver()** instance so the caller can use it directly (e.g. **compile(checkpointer=get_checkpointer())**).

```python
def get_checkpointer():
    """
    Return a checkpointer for the graph: PostgresSaver context manager or MemorySaver.

    Use cases: callers that support both DB and in-memory. When DATABASE_URL is set,
    return the postgres_checkpointer() context manager; otherwise return a MemorySaver
    instance so the caller can use it directly.
    """
```

- **Returns:** Either the **postgres_checkpointer()** context manager (caller must enter it with **with** to get the **PostgresSaver**) or a **MemorySaver()** instance. So the caller’s usage differs: for Postgres they need **with get_checkpointer() as cp: graph = build_email_assistant_graph(); compiled = graph.compile(checkpointer=cp)** (or similar); for MemorySaver they can do **cp = get_checkpointer(); compiled = graph.compile(checkpointer=cp)**.
- **Docstring:** Explains the two cases: **DATABASE_URL** set → context manager; not set → **MemorySaver** for direct use.

```python
    if os.getenv("DATABASE_URL"):
        return postgres_checkpointer()
    return MemorySaver()
```

- **If DATABASE_URL is set:** Return **postgres_checkpointer()** (the context manager object). The caller must use **with get_checkpointer() as cp: ...** to get the actual **PostgresSaver** and ensure the connection is closed.
- **Else:** Return a new **MemorySaver()** instance. No context manager; the caller can pass it directly to **compile(checkpointer=...)**. State is in-memory only and lost when the process exits.

---

## 6. Flow summary

1. **Scripts (e.g. run_agent.py, setup_db.py):** When using Postgres, call **with get_checkpointer() as cp:** (or **with postgres_checkpointer() as cp:**) and pass **cp** to **build_email_assistant_graph(checkpointer=cp)** or **compile(checkpointer=cp)**. When not using Postgres, **get_checkpointer()** returns **MemorySaver()** and the caller passes it directly.
2. **postgres_checkpointer():** Opens one connection with **search_path=email_assistant** and **prepare_threshold=None**, yields **PostgresSaver(conn)**, closes the connection on exit. Checkpoint tables must already exist (e.g. created by **scripts/setup_db.py** calling **cp.setup()`).
3. **run_checkpoint_created_at_migration():** Opens a connection, sets **search_path**, runs **002_checkpoint_created_at.sql** (add **created_at** to checkpoint tables), closes the connection. Run once (e.g. after **setup()**) from **scripts/setup_db.py**.
4. **get_checkpointer():** Branches on **DATABASE_URL** to return either the Postgres context manager or a **MemorySaver**, so callers can support both persistent (Postgres) and in-memory checkpointing.

---

## 7. Related files

- **Graph compile:** `src/email_assistant/email_assistant_hitl_memory_gmail.py` (**build_email_assistant_graph(checkpointer=...)**). CLI scripts pass the checkpointer from **get_checkpointer()** or **postgres_checkpointer()**.
- **Setup script:** **scripts/setup_db.py** (typically creates checkpoint tables via **PostgresSaver.setup()** and runs **run_checkpoint_created_at_migration()**).
- **Migration:** **migrations/002_checkpoint_created_at.sql** (adds **created_at** to checkpoint tables).
- **HITL / interrupt:** Checkpointer is required for **interrupt()** in **triage_interrupt_handler**; state is persisted at interrupt and restored on resume.

For where the checkpointer is passed into the graph, see **docs/code-explanations/email_assistant_hitl_memory_gmail.md**. For database and checkpoint tables, see **docs/DATABASE.md** or **docs/guide/05_DATABASE_AND_PERSISTENCE.md** if present.
