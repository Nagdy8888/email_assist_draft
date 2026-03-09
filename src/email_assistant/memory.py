"""
get_memory and update_memory (store-agnostic) for user preferences.

Use cases: read/write triage_preferences, response_preferences, cal_preferences
from the LangGraph store; nodes receive store via closure or compile(store=...).
"""

from typing import Any, Optional

# Namespaces for user preferences (per user, chat_id = NULL in agent_memory).
PREFERENCE_NAMESPACES = ("triage_preferences", "response_preferences", "cal_preferences")


def get_memory(store: Any, user_id: str, namespace: str) -> Optional[str]:
    """
    Read user preference text for a given namespace from the store.

    Use cases: triage_router loads triage_instructions; response agent loads
    response_preferences and cal_preferences for the system prompt.

    Args:
        store: LangGraph BaseStore (e.g. PostgresStore); must support get(namespace, key).
        user_id: User identifier (preferences are per user).
        namespace: One of triage_preferences, response_preferences, cal_preferences.

    Returns:
        Stored string or None if not set.
    """
    if store is None:
        return None
    try:
        # LangGraph store: namespace is a tuple path; we use ("user_preferences", user_id), key = namespace.
        ns = ("user_preferences", str(user_id))
        result = store.get(ns, namespace)
        if result is None:
            return None
        # Some stores return an object with .value
        if hasattr(result, "value"):
            val = result.value
        else:
            val = result
        if isinstance(val, str):
            return val
        if isinstance(val, dict) and "content" in val:
            return val["content"]
        return str(val) if val is not None else None
    except Exception:
        return None


def update_memory(store: Any, user_id: str, namespace: str, value: str) -> None:
    """
    Write user preference text for a given namespace to the store.

    Use cases: after user feedback (e.g. notify choice, or explicit preference),
    call memory-update LLM then update_memory to persist.

    Args:
        store: LangGraph BaseStore; must support put(namespace, key, value).
        user_id: User identifier.
        namespace: One of triage_preferences, response_preferences, cal_preferences.
        value: Full preference text to store (string).
    """
    if store is None:
        return
    try:
        ns = ("user_preferences", str(user_id))
        # Store as dict so we can extend later; consumers expect string so get_memory returns content.
        store.put(ns, namespace, {"content": value})
    except Exception:
        pass
