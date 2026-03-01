"""
prepare_messages: inject reply context into messages before the Response subgraph when email_id/email_input set.

Use cases: runs between input_router (or Email Assistant subgraph) and Response subgraph;
ensures the agent sees "reply to this email" context and email_id when on the respond path.
"""

from langchain_core.messages import HumanMessage

from email_assistant.schemas import State


def prepare_messages(state: State) -> dict:
    """
    If email_id and email_input are set, prepend a HumanMessage with reply context to state["messages"].
    Otherwise return {} (messages already set by input_router for question mode).

    Use cases: question path — no change. Respond path — agent gets reply context and email_id for send_email_tool.
    """
    email_id = state.get("email_id")
    email_input = state.get("email_input")
    if not email_id or not email_input:
        return {}
    messages = list(state.get("messages") or [])
    from_addr = (email_input.get("from") or "").strip()
    subject = (email_input.get("subject") or "").strip()
    body = str(email_input.get("body", ""))[:4000]
    from_gmail = email_input.get("_source") == "gmail"
    prefix = "This email just arrived in the user's Gmail inbox. " if from_gmail else ""
    inject = (
        f"{prefix}You are replying to an email. Use send_email_tool with email_id='{email_id}' to send your reply. "
        f"From: {from_addr}\nSubject: {subject}\n\nBody:\n{body}"
    )
    return {"messages": [HumanMessage(content=inject)] + messages}
