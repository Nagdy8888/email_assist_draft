"""
triage_router: classify email as ignore / notify / respond using RouterSchema.

Use cases: single LLM call with structured output; uses triage prompts and memory.
"""

import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from email_assistant.prompts import get_triage_system_prompt, get_triage_user_prompt
from email_assistant.schemas import RouterSchema, State


def triage_router(state: State) -> dict:
    """
    Run triage LLM with structured output (RouterSchema). Return classification_decision and optionally reasoning.

    Use cases: after input_router when email_input is present; output drives conditional edges (ignore/notify/respond).
    """
    email_input = state.get("email_input")
    if not email_input:
        return {"classification_decision": "ignore"}
    from_addr = email_input.get("from", "")
    to_addr = email_input.get("to", "")
    subject = email_input.get("subject", "")
    body = str(email_input.get("body", ""))[:8000]
    from_gmail_inbox = email_input.get("_source") == "gmail"
    system = get_triage_system_prompt()
    user = get_triage_user_prompt(from_addr, to_addr, subject, body, from_gmail_inbox=from_gmail_inbox)
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    structured = llm.with_structured_output(RouterSchema)
    result = structured.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    classification = (result.get("classification") or "ignore").strip().lower()
    if classification not in ("ignore", "notify", "respond"):
        classification = "ignore"
    return {
        "classification_decision": classification,
    }
