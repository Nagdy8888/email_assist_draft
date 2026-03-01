"""
triage_interrupt_handler: HITL after notify; user chooses respond or ignore.

Use cases: handle interrupt, resume with Command(resume=...) (e.g. "respond" or "ignore");
the resume value becomes the return value of interrupt() and we return _notify_choice for routing.
"""

from langgraph.types import interrupt

from email_assistant.schemas import State


def triage_interrupt_handler(state: State) -> dict:
    """
    On first run: interrupt with a payload so the user can choose respond or ignore.
    When resumed via Command(resume="respond") or Command(resume="ignore"), return _notify_choice for conditional edge.

    Use cases: after triage_router when classification is notify; graph pauses until user resumes with respond/ignore.
    """
    choice = interrupt({
        "message": "Email was classified as 'notify'. Choose: respond or ignore?",
        "email_subject": (state.get("email_input") or {}).get("subject", ""),
        "expected_resume_values": ["respond", "ignore"],
    })
    # When resumed, choice is the value passed to Command(resume=...)
    if isinstance(choice, str):
        choice = choice.strip().lower()
    if choice == "respond" or choice is True:
        return {"_notify_choice": "respond"}
    return {"_notify_choice": "ignore"}


def after_triage_interrupt_route(state: State) -> str:
    """Return next node name after triage_interrupt: 'response_agent' or '__end__'."""
    ch = (state.get("_notify_choice") or "").strip().lower()
    if ch == "respond":
        return "response_agent"
    return "__end__"
