"""
Wrapper/config for PostgresSaver (LangGraph checkpointer).

Use cases: create checkpointer from DATABASE_URL; call setup() for checkpoint tables;
pass into graph compile(checkpointer=...). Use postgres_checkpointer() as a context
manager when DATABASE_URL is set; otherwise use MemorySaver in the caller.
"""

import os
from contextlib import contextmanager
from typing import Iterator

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver


@contextmanager
def postgres_checkpointer() -> Iterator[PostgresSaver]:
    """
    Yield a PostgresSaver for DATABASE_URL; runs setup() on first use.

    Use cases: use in run_agent or app startup when DATABASE_URL is set.
    Creates LangGraph checkpoint tables (checkpoints, checkpoint_blobs, etc.) via setup().
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is required for postgres checkpointer")
    with PostgresSaver.from_conn_string(url) as checkpointer:
        checkpointer.setup()
        yield checkpointer


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
