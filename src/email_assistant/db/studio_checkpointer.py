"""
Async checkpointer for LangGraph Studio (langgraph dev).

Use cases: yield an AsyncPostgresSaver with search_path=email_assistant so Studio
uses the same Supabase Postgres as CLI scripts. Referenced by langgraph.json
checkpointer.path. Run setup() on entry so checkpoint tables exist in email_assistant.
Uses a single connection with prepare_threshold=None (Supabase-friendly); the server
keeps the context open for the duration of the server so checkpoints persist.
"""

import contextlib
import os

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row


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
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is required for Studio checkpointer. Set it in .env and restart langgraph dev.")
    conn = await AsyncConnection.connect(
        url, autocommit=True, prepare_threshold=None, row_factory=dict_row
    )
    try:
        async with conn.cursor() as cur:
            await cur.execute("SET search_path TO email_assistant")
        saver = AsyncPostgresSaver(conn)
        await saver.setup()
        yield saver
    finally:
        await conn.close()
