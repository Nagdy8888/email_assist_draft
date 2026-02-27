"""
Create LangGraph checkpoint tables and store table in Postgres (Phase 3).

Use cases: run once after setting DATABASE_URL. Creates tables for PostgresSaver
and PostgresStore. Application tables (users, chats, messages, agent_memory) must
be created separately by running migrations/001_email_assistant_tables.sql.
"""

import os
import sys

from dotenv import load_dotenv

from email_assistant.db.checkpointer import postgres_checkpointer
from email_assistant.db.store import setup_store


def main() -> None:
    load_dotenv()
    if not os.getenv("DATABASE_URL"):
        print("DATABASE_URL is not set. Set it in .env and run again.")
        sys.exit(1)
    print("Setting up LangGraph checkpointer tables...")
    with postgres_checkpointer() as _:
        pass  # setup() is called inside the context
    print("Checkpointer tables created.")
    print("Setting up LangGraph store table...")
    setup_store()
    print("Store table created.")
    print("Done. Ensure migrations/001_email_assistant_tables.sql has been run for app tables.")


if __name__ == "__main__":
    main()
