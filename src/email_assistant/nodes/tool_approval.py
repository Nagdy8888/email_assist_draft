"""
Tool approval gate: interrupt before executing send_email_tool or schedule_meeting_tool so the user can approve.

Use cases: Phase 6 HITL; when the LLM requests send_email or schedule_meeting, the graph pauses,
shows pending tool calls, and resumes with Command(resume=True) to run or Command(resume=False) to decline.
"""

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import interrupt

from email_assistant.schemas import State

TOOLS_REQUIRING_APPROVAL = ("send_email_tool", "schedule_meeting_tool")
APPROVAL_INTERRUPT_MESSAGE = "Approve sending email / scheduling meeting? Pending tool calls above. Resume with True to run, False to decline."


def tool_approval_gate(state: State) -> dict:
    """
    If the last message has tool_calls for send_email_tool or schedule_meeting_tool, interrupt for approval.
    On resume with False, inject ToolMessages (User declined) and set _tool_approval to False so we route to chat.
    On resume with True, set _tool_approval to True and proceed to tools node.

    Use cases: response subgraph runs chat -> tool_approval_gate -> (tools or chat). Requires checkpointer.
    """
    messages = state.get("messages") or []
    if not messages:
        return {}
    last = messages[-1]
    if not isinstance(last, AIMessage) or not getattr(last, "tool_calls", None):
        return {"_tool_approval": True}

    tool_calls = last.tool_calls or []
    to_approve = [tc for tc in tool_calls if (tc.get("name") or "") in TOOLS_REQUIRING_APPROVAL]
    if not to_approve:
        return {"_tool_approval": True}

    choice = interrupt({
        "message": APPROVAL_INTERRUPT_MESSAGE,
        "tool_calls": [{"name": tc.get("name"), "args": tc.get("args")} for tc in to_approve],
    })

    if choice is True:
        return {"_tool_approval": True}
    # User declined: inject ToolMessages so the agent sees "User declined" and can respond.
    declined_messages = [
        ToolMessage(content="User declined to send email / schedule meeting.", tool_call_id=tc.get("id", ""))
        for tc in to_approve
    ]
    return {"messages": declined_messages, "_tool_approval": False}
