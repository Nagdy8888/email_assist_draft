"""
triage_interrupt_handler: when classification is notify, pause for human choice (respond or ignore).

Use cases: after triage_router when classification is notify; calls interrupt() so the
graph pauses and the user can resume with Command(resume="respond") or Command(resume="ignore").
Requires a checkpointer (e.g. Postgres or MemorySaver) for interrupt to work.
"""

from langgraph.types import interrupt

from email_assistant.schemas import State


# Payload shown to the user when the graph is waiting for respond/ignore (e.g. in Studio).
NOTIFY_INTERRUPT_MESSAGE = {
    "message": "This email was classified as **notify** (FYI). Should the assistant respond or ignore?",
    "options": ["respond", "ignore"],
}


def triage_interrupt_handler(state: State) -> dict:
    """
    When classification is notify, pause and wait for human choice; return _notify_choice.

    Use cases: after triage_router when classification is notify. Calls interrupt() so
    the graph pauses; the caller (Studio or run_agent.py / run_mock_email.py) resumes with
    Command(resume="respond") or Command(resume="ignore"). The resume value becomes the
    return value of interrupt() and is written to _notify_choice.
    """
    # Pause for human decision. On resume, Command(resume="respond") or Command(resume="ignore")
    # is passed here as choice.
    choice = interrupt(NOTIFY_INTERRUPT_MESSAGE)
    if isinstance(choice, str):
        choice = choice.strip().lower()
    else:
        choice = "ignore"
    if choice not in ("respond", "ignore"):
        choice = "ignore"
    return {"_notify_choice": choice}
