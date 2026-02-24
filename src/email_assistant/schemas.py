"""
State, StateInput, RouterSchema, and UserPreferences for the email assistant graph.

Use cases: define graph state (messages, email_input, classification_decision),
input types for email vs question mode, and structured outputs for triage and memory.
"""

from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages

# Phase 2: minimal state for simple agent (messages only).
# Later phases add email_input, classification_decision, etc.
MessagesState = TypedDict(
    "MessagesState",
    {"messages": Annotated[list, add_messages]},
)
