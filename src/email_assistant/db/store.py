"""
Store for memory: PostgresStore (LangGraph built-in) from DATABASE_URL.

Use cases: back get_memory/update_memory with LangGraph's store table; pass into
graph compile(store=...) when using memory (Phase 6). For Phase 3 the simple agent
does not use the store; setup_store() is called from scripts/setup_db.py.
"""

import os
from contextlib import contextmanager
from typing import Iterator

from langgraph.store.postgres import PostgresStore


@contextmanager
def postgres_store() -> Iterator[PostgresStore]:
    """
    Yield a PostgresStore for DATABASE_URL.

    Use cases: compile graph with store=... when using memory; or call setup()
    inside this context to create the store table.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is required for postgres store")
    with PostgresStore.from_conn_string(url) as store:
        yield store


def setup_store() -> None:
    """
    Create the LangGraph store table in Postgres (idempotent).

    Use cases: run once before using the store, e.g. from scripts/setup_db.py.
    """
    with postgres_store() as store:
        store.setup()
