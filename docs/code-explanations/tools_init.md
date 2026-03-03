# Explanation: `tools/__init__.py`

Detailed walkthrough of the **tools** package entry point: it exposes **get_tools(include_gmail=...)** and the tool imports used by the response agent. Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–6)

```python
"""
get_tools(include_gmail=...) and tool exports for the response agent.

Use cases: provide send_email_tool, fetch_emails_tool, check_calendar_tool,
schedule_meeting_tool, Question, Done to the LLM via bind_tools.
"""
```

- **Line 2:** This module is the **tools** package entry point. It defines **get_tools(include_gmail=...)** and re-exports the tools used by the response agent (chat/tool-call loop).
- **Lines 4–5:** **Use cases:** The list is meant to include **send_email_tool**, **fetch_emails_tool**, **check_calendar_tool**, **schedule_meeting_tool**, and the **Question** / **Done**-style tools (here implemented as **question_tool** and **done_tool**). These are passed to the LLM via **bind_tools()**. The current implementation provides **send_email_tool**, **question_tool**, and **done_tool**; fetch/calendar/schedule may be added later or live in other modules.

---

## 2. Imports (lines 8–9)

```python
from email_assistant.tools.common import done_tool, question_tool
from email_assistant.tools.gmail.send_email import send_email_tool
```

- **done_tool:** Tool the LLM can call when it has finished the user’s request (e.g. “I’ve sent the email”). Defined in **email_assistant.tools.common**.
- **question_tool:** Tool the LLM uses to ask the user for clarification (e.g. “Which address should I send this to?”). Defined in **email_assistant.tools.common**.
- **send_email_tool:** Tool to send a new email or a reply (with **email_address**, **subject**, **body**, and optionally **email_id** for replies). Defined in **email_assistant.tools.gmail.send_email**.

---

## 3. `get_tools` (lines 12–24)

**Purpose:** Return the list of tools to pass to **ChatOpenAI.bind_tools()** in the response subgraph. When **include_gmail** is True, **send_email_tool** is included (and placed first); the list always includes **question_tool** and **done_tool**.

```python
def get_tools(include_gmail: bool = True):
    """
    Return list of tools for the response agent LLM (bind_tools).

    Use cases: pass to ChatOpenAI.bind_tools() in the chat/tool-call loop.
    Phase 4: send_email_tool, question_tool, done_tool. Optional fetch/calendar later.
    """
```

- **include_gmail:** When **True** (default), **send_email_tool** is included. When **False**, only **question_tool** and **done_tool** are returned (e.g. for a non-email or test mode).
- **Returns:** A list of tool objects (LangChain/LangGraph tool callables) that the LLM can invoke. This list must match what **ToolNode** receives in **simple_agent.py** so tool names and schemas align.
- **Docstring:** The list is passed to **bind_tools()** in the chat node. Phase 4 delivers send_email, question, and done; fetch/calendar tools are optional and may be added later.

```python
    tools = [question_tool, done_tool]
```

- **tools:** Base list with **question_tool** and **done_tool** only. Order is preserved; we insert **send_email_tool** at index 0 when Gmail is included so it appears first in the tool list (convention only; the LLM can call any tool by name).

```python
    if include_gmail:
        tools.insert(0, send_email_tool)
    return tools
```

- **if include_gmail:** When True, **send_email_tool** is inserted at position **0**, so the final list is **[send_email_tool, question_tool, done_tool]**.
- **return tools:** Return the list. Callers (e.g. **_chat_node** and **build_response_subgraph** in **simple_agent.py**) use this for **llm.bind_tools(tools)** and **ToolNode(tools)** so the same tool set is bound to the LLM and executed by the tool node.

---

## 4. Flow summary

1. **simple_agent.py** calls **get_tools(include_gmail=True)** in both **_chat_node** (for **llm.bind_tools(tools)**) and **build_response_subgraph** (for **ToolNode(tools)**). The same list must be used in both places so the LLM’s tool_calls match the ToolNode’s tools.
2. **include_gmail=True** (default): tools = **[send_email_tool, question_tool, done_tool]**.
3. **include_gmail=False**: tools = **[question_tool, done_tool]** (no send_email).
4. The response agent’s system prompt (in **prompts.py**) describes when to use **send_email_tool**, **question_tool**, and **done_tool**; the LLM chooses from this list and ToolNode executes the corresponding function.

---

## 5. Related files

- **Response subgraph / chat node:** `src/email_assistant/simple_agent.py` (calls **get_tools(include_gmail=True)** for **bind_tools** and **ToolNode**).
- **Common tools:** `src/email_assistant/tools/common.py` (**question_tool**, **done_tool**).
- **Send email:** `src/email_assistant/tools/gmail/send_email.py` (**send_email_tool**).
- **Agent prompt:** `src/email_assistant/prompts.py` (**get_agent_system_prompt_with_tools** describes how to use these tools).

For the chat/tool loop and ToolNode, see **docs/code-explanations/simple_agent.md**. For prompt text, see **docs/code-explanations/prompts.md**.
