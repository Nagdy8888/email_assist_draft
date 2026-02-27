"""
Persist conversation messages to email_assistant.chats and email_assistant.messages.

Use cases: after each graph run, sync state["messages"] to Postgres for queryable
chat history (Phase 3). Uses thread_id as stable chat_id (UUID5) and user_id from config/env.
"""

import json
import uuid
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from psycopg import Connection
from psycopg.rows import dict_row

# Stable namespace for deriving chat_id from thread_id (string) so same thread_id => same chat_id.
THREAD_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "email_assistant.chat_id")


def _message_role(msg: BaseMessage) -> str:
    """Map LangChain message type to email_assistant.messages.role."""
    if isinstance(msg, HumanMessage):
        return "user"
    if isinstance(msg, AIMessage):
        return "assistant"
    if isinstance(msg, SystemMessage):
        return "system"
    return "tool"


def _message_content(msg: BaseMessage) -> str | None:
    """Extract content for DB; prefer string content."""
    content = getattr(msg, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Multimodal: could join text parts; for Phase 3 store repr or first text
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                return part.get("text", "")
        return str(content)[:10000]
    return str(content) if content is not None else None


def thread_id_to_chat_id(thread_id: str) -> uuid.UUID:
    """Return a stable UUID for the chat from thread_id (for DB chats.chat_id)."""
    return uuid.uuid5(THREAD_NAMESPACE, thread_id)


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
    chat_id = thread_id_to_chat_id(thread_id)
    try:
        u = uuid.UUID(user_id)
    except (ValueError, TypeError):
        u = uuid.uuid5(THREAD_NAMESPACE, f"user_{user_id}")

    with Connection.connect(conn_string, autocommit=True, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # Ensure user exists
            cur.execute(
                """
                INSERT INTO email_assistant.users (user_id, updated_at)
                VALUES (%s, now())
                ON CONFLICT (user_id) DO UPDATE SET updated_at = now()
                """,
                (u,),
            )
            # Ensure chat exists
            cur.execute(
                """
                INSERT INTO email_assistant.chats (chat_id, user_id, updated_at)
                VALUES (%s, %s, now())
                ON CONFLICT (chat_id) DO UPDATE SET updated_at = now()
                """,
                (chat_id, u),
            )
            # Replace messages for this chat (sync full conversation; avoids duplicates when graph runs each turn)
            cur.execute(
                "DELETE FROM email_assistant.messages WHERE chat_id = %s",
                (chat_id,),
            )
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
