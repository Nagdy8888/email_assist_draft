"""
State, StateInput, RouterSchema, and UserPreferences for the email assistant graph.

Use cases: define graph state (messages, email_input, classification_decision),
input types for email vs question mode, and structured outputs for triage and memory.
"""

from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages

# Phase 2: minimal state for simple agent (messages only).
MessagesState = TypedDict(
    "MessagesState",
    {"messages": Annotated[list, add_messages]},
)

# Phase 5: classification from triage router.
ClassificationDecision = Literal["ignore", "notify", "respond"]

# Phase 5: extended state for top-level graph (email mode + question mode).
State = TypedDict(
    "State",
    {
        "messages": Annotated[list, add_messages],
        "email_input": Optional[dict],
        "classification_decision": Optional[ClassificationDecision],
        "email_id": Optional[str],
        "_notify_choice": Optional[str],  # "respond" | "ignore" after triage_interrupt (user resumes with Command(resume=...))
        "_tool_approval": Optional[bool],  # True = run tools (send_email/schedule_meeting approved); False = declined
        "user_message": Optional[str],
        "question": Optional[str],
    },
)

# Phase 5: input can be email payload (email mode) or user message (question mode).
StateInput = TypedDict(
    "StateInput",
    {
        "messages": Annotated[list, add_messages],
        "email_input": Optional[dict],
        "user_message": Optional[str],
        "question": Optional[str],
    },
    total=False,
)

# Phase 5: structured output from triage LLM.
RouterSchema = TypedDict(
    "RouterSchema",
    {
        "reasoning": str,
        "classification": ClassificationDecision,
    },
)

# Phase 5: auto-decision when classification is notify (no HITL).
NotifyChoiceSchema = TypedDict(
    "NotifyChoiceSchema",
    {"choice": Literal["respond", "ignore"]},
)
