# Explanation: `nodes/prepare_messages.py`

Detailed walkthrough of the **prepare_messages** node: it injects reply context into **state["messages"]** before the Response subgraph when we're on the **respond** path (email_id and email_input set). Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–6)

```python
"""
prepare_messages: inject reply context into messages before the Response subgraph when email_id/email_input set.

Use cases: runs between input_router (or Email Assistant subgraph) and Response subgraph;
ensures the agent sees "reply to this email" context and email_id when on the respond path.
"""
```

- **Line 2:** This module implements **prepare_messages**, which **injects reply context** into the messages list when **email_id** and **email_input** are set, so the Response subgraph knows we're replying to a specific email.
- **Lines 4–5:** **Use cases:** The node runs **after** either (1) **input_router** (when we went straight to prepare_messages in question mode) or (2) the **Email Assistant subgraph** (when triage or HITL chose **respond**). It sits **before** the Response subgraph. On the respond path it ensures the agent sees “reply to this email” context and the **email_id** (for **send_email_tool**); on the question path it does nothing.

---

## 2. Imports (lines 8–10)

```python
from langchain_core.messages import HumanMessage
```

- **HumanMessage:** Used to build the injected message. We prepend a **HumanMessage** whose content is the reply context (instructions + from/subject/body snippet) so the LLM in the response subgraph treats it as the user’s “reply to this email” request.

```python
from email_assistant.schemas import State
```

- **State:** Graph state type. The node reads **email_id**, **email_input**, and **messages**, and returns **{"messages": [inject] + messages}** when on the respond path.

---

## 3. `prepare_messages` (lines 13–34)

**Purpose:** When **email_id** and **email_input** are both set, prepend a **HumanMessage** containing reply context (and optional Gmail inbox note) to **state["messages"]**. Otherwise return **{}** so state is unchanged. The Response subgraph then sees the injected message and can use **send_email_tool** with **email_id** to send the reply.

```python
def prepare_messages(state: State) -> dict:
    """
    If email_id and email_input are set, prepend a HumanMessage with reply context to state["messages"].
    Otherwise return {} (messages already set by input_router for question mode).

    Use cases: question path — no change. Respond path — agent gets reply context and email_id for send_email_tool.
    """
```

- **state:** Current graph state. We need **email_id** (Gmail message id for the reply) and **email_input** (normalized email with from, to, subject, body, _source).
- **Returns:** Either **{}** (no update) or **{"messages": [inject] + messages}**. Because **State** uses **add_messages** for **messages**, returning **{"messages": [HumanMessage(...)] + messages}** effectively **prepends** that message to the conversation (the reducer appends the list we return to existing messages; here we’re passing “new” messages = one inject + previous messages, so the net effect is inject first then previous messages).
- **Docstring:** Question path → no change (input_router already set messages). Respond path → agent gets reply context and **email_id** for **send_email_tool**.

```python
    email_id = state.get("email_id")
    email_input = state.get("email_input")
    if not email_id or not email_input:
        return {}
```

- **email_id:** Set by **input_router** when the normalized email had an **id** (Gmail message id). Required for **send_email_tool** when replying.
- **email_input:** Normalized email dict from **input_router** (from, to, subject, body, _source, etc.).
- If either is missing, we're not on the “reply to this email” path (e.g. question mode or no email). Return **{}** so we don’t change state. The Response subgraph still runs with whatever **messages** already exist (e.g. from input_router in question mode).

```python
    messages = list(state.get("messages") or [])
```

- **messages:** Copy of the current conversation list. We'll prepend the reply-context message to this list and return it. Using **list(...)** avoids mutating the original sequence.

```python
    from_addr = (email_input.get("from") or "").strip()
    subject = (email_input.get("subject") or "").strip()
    body = str(email_input.get("body", ""))[:4000]
```

- **from_addr, subject:** For the injected message so the agent knows who the email is from and what the subject is. Stripped for cleanliness.
- **body:** Email body as string, truncated to **4000** characters so the inject stays within a reasonable token size while still giving the agent enough context to draft a reply.

```python
    from_gmail = email_input.get("_source") == "gmail"
    prefix = "This email just arrived in the user's Gmail inbox. " if from_gmail else ""
```

- **from_gmail:** True when **input_router** set **_source** to **"gmail"** (incoming Gmail message). Same meaning as in the triage node.
- **prefix:** When the email is from Gmail inbox, we add a short note so the agent knows it’s an incoming message. Otherwise **prefix** is empty.

```python
    inject = (
        f"{prefix}You are replying to an email. Use send_email_tool with email_id='{email_id}' to send your reply. "
        f"From: {from_addr}\nSubject: {subject}\n\nBody:\n{body}"
    )
```

- **inject:** The content of the single **HumanMessage** we prepend. It tells the agent:
  1. Optional **prefix** (“This email just arrived in the user’s Gmail inbox. ”).
  2. “You are replying to an email. Use send_email_tool with email_id='...' to send your reply.” — so the agent knows to call **send_email_tool** with **email_id**.
  3. “From: … Subject: … Body: …” — so the agent has the original email context to draft the reply.

```python
    return {"messages": [HumanMessage(content=inject)] + messages}
```

- Return a state update with **messages** set to **[inject message] + existing messages**. LangGraph merges this using the **add_messages** reducer: the effect is that the reply-context message appears first, then the rest of the conversation. The Response subgraph’s chat node will see this as the latest user turn and can use **email_id** and the body snippet to generate and send the reply.

---

## 4. Flow summary

1. **prepare_messages** runs after either:
   - **input_router** (question path: we went straight to prepare_messages), or  
   - **email_assistant** subgraph (respond path: triage or _notify_choice was “respond”).
2. **Question path:** Usually **email_id** and **email_input** are not set (or only one is). Node returns **{}**; **messages** were already set by **input_router** (e.g. one **HumanMessage** with the user’s question).
3. **Respond path:** **email_id** and **email_input** are set. Node builds **inject** (prefix + instructions + from/subject/body), then returns **{"messages": [HumanMessage(content=inject)] + messages}**. Response subgraph runs with this; the agent sees “reply to this email” and **email_id** and can call **send_email_tool** with **email_id** to send the reply.
4. After **prepare_messages**, the graph always goes to **response_agent** → **mark_as_read** → END.

---

## 5. Related files

- **State:** `src/email_assistant/schemas.py` (**messages**, **email_id**, **email_input**).
- **Graph wiring:** `src/email_assistant/email_assistant_hitl_memory_gmail.py` (conditional edges: **email_assistant** or **input_router** → **prepare_messages** → **response_agent**).
- **input_router:** `src/email_assistant/nodes/input_router.py` (sets **email_input**, **email_id** when normalizing an email).
- **Response subgraph:** `src/email_assistant/simple_agent.py` (**_chat_node** uses **messages**; tools include **send_email_tool** with **email_id** for replies).

For the top-level flow and routing, see **docs/code-explanations/email_assistant_hitl_memory_gmail.md**. For state and reducers, see **docs/code-explanations/schemas.md**.
