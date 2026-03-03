"""
Wrapper/config for PostgresSaver (LangGraph checkpointer).

Use cases: create checkpointer from DATABASE_URL; call setup() for checkpoint tables;
pass into graph compile(checkpointer=...). Use postgres_checkpointer() as a context
manager when DATABASE_URL is set; otherwise use MemorySaver in the caller.
Checkpoint tables are created in the email_assistant schema via search_path.
"""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection
from psycopg.rows import dict_row


@contextmanager
def postgres_checkpointer() -> Iterator[PostgresSaver]:
    """
    Yield a PostgresSaver for DATABASE_URL with search_path=email_assistant.
    Does not run setup(); run scripts/setup_db.py once to create checkpoint tables
    and avoid DuplicatePreparedStatement when using pooled connections (e.g. Supabase).
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is required for postgres checkpointer")
    conn = Connection.connect(
        url, autocommit=True, prepare_threshold=None, row_factory=dict_row
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO email_assistant")
        yield PostgresSaver(conn)
    finally:
        conn.close()


def run_checkpoint_created_at_migration(migration_path: Optional[Path] = None) -> None:
    """
    Run migrations/002_checkpoint_created_at.sql to add created_at to checkpoint tables.

    Use cases: call from scripts/setup_db.py after cp.setup(). Opens a connection
    with search_path=email_assistant, executes the SQL, closes. Idempotent.
    """
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
    conn = Connection.connect(
        url, autocommit=True, prepare_threshold=None, row_factory=dict_row
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO email_assistant")
            cur.execute(sql)
    finally:
        conn.close()


def get_checkpointer():
    """
    Return a checkpointer for the graph: PostgresSaver context manager or MemorySaver.

    Use cases: callers that support both DB and in-memory. When DATABASE_URL is set,
    return the postgres_checkpointer() context manager; otherwise return a MemorySaver
    instance so the caller can use it directly.
    """
    if os.getenv("DATABASE_URL"):
        return postgres_checkpointer()
    return MemorySaver()
