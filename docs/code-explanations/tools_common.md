# Explanation: `tools/common.py`

Detailed walkthrough of the **common** tools used by the response agent: **question_tool** (ask the user for clarification) and **done_tool** (signal end of turn). Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–6)

```python
"""
Question and Done tools for the response agent.

Use cases: agent signals need for clarification (Question) or completion (Done);
used in tool-call loop so the agent can ask the user or signal end of turn.
"""
```

- **Line 2:** This module defines the **Question** and **Done** tools: **question_tool** and **done_tool**, used by the response agent in the chat/tool-call loop.
- **Lines 4–5:** **Use cases:** The agent calls **question_tool** when it needs more information (e.g. missing recipient, unclear request) so the user sees a clarification question. It calls **done_tool** when it has finished the request (e.g. after sending an email) to signal completion. Both are part of the tool-call loop so the LLM can choose to ask or finish instead of only calling send_email.

---

## 2. Import (line 8)

```python
from langchain_core.tools import tool
```

- **tool:** LangChain decorator that turns a Python function into a **tool** the LLM can call. The decorator uses the function’s name, docstring, and parameter annotations to build a schema (name, description, parameters) for the LLM. The function is invoked by **ToolNode** when the LLM outputs a tool_call with this tool’s name and arguments.

---

## 3. `question_tool` (lines 11–17)

**Purpose:** Tool the agent uses to ask the user a question or request clarification. When the LLM calls it with a **message**, the function returns a string that is added to the conversation as a tool result; the user (or UI) can interpret it and respond in the next turn.

```python
@tool
def question_tool(message: str) -> str:
```

- **@tool:** Registers the function as a LangChain tool. The LLM sees a tool named **question_tool** (or the schema’s name) with one parameter **message** (string). When the model decides it needs clarification, it issues a tool_call with **message** set to the question text.
- **message:** The question or clarification request (e.g. “Which email address should I send this to?”, “What subject line do you want?”). The agent is expected to fill this from its reasoning.
- **Returns:** A string that becomes the **tool result** appended to **messages** (as a ToolMessage). The response agent’s prompt tells the model to use **question_tool** when it needs more info; the returned string is for the conversation history and for the user/UI to show or act on.

```python
    """
    Ask the user a question or request clarification. Use when you need more information
    (e.g. missing recipient, unclear subject) before proceeding.
    """
```

- **Docstring:** Becomes the tool’s **description** in the schema sent to the LLM. It tells the model when to use this tool: when it needs more information (e.g. missing recipient, unclear subject) before it can proceed. So the model learns to call **question_tool** instead of guessing or making up data.

```python
    return f"[Question for user: {message}]"
```

- **Return value:** Wraps the agent’s **message** in a fixed format **"[Question for user: ...]"**. This string is stored as the tool result in the conversation. The UI or downstream logic can detect this pattern to show the question to the user or trigger a clarification flow. The agent doesn’t perform an external API call here; it only records the question in the thread.

---

## 4. `done_tool` (lines 20–26)

**Purpose:** Tool the agent uses to signal that it has finished this turn. Optionally includes a short summary of what was done (e.g. “Sent email to alice@example.com”). The return value is stored as the tool result; the graph can continue to the next node (e.g. persist_messages, then END).

```python
@tool
def done_tool(summary: str = "") -> str:
```

- **@tool:** Registers the function as a tool. The LLM sees **done_tool** with one optional parameter **summary**.
- **summary:** Optional short description of what was completed (e.g. “Sent reply to the Q4 report request”). Default **""** so the agent can call **done_tool()** with no args to simply signal “I’m done.”
- **Returns:** A string that becomes the tool result in the conversation. Used so the turn has a clear “done” tool call and, if provided, a human-readable summary.

```python
    """
    Signal that you are done with this turn. Use after sending an email or completing
    the user's request. Optionally provide a short summary of what was done.
    """
```

- **Docstring:** Tool description for the LLM. Tells the model to use **done_tool** after sending an email or completing the request, and that it can optionally pass a summary. This encourages the model to call **done_tool** when finished instead of leaving the turn open or making another tool call.

```python
    return f"Done.{' ' + summary if summary else ''}"
```

- **Return value:** **"Done."** when **summary** is empty, or **"Done. " + summary** when **summary** is non-empty. This string is the tool result. It gives a consistent “done” marker and, when present, a brief record of what was done for the conversation history and for the user.

---

## 5. Flow summary

1. **get_tools()** in **tools/__init__.py** includes **question_tool** and **done_tool** in the list passed to **bind_tools** and **ToolNode** in the response subgraph.
2. **question_tool:** When the LLM needs clarification, it emits a tool_call to **question_tool** with **message="..."**. **ToolNode** runs the function; the return value **"[Question for user: ...]"** is appended as a ToolMessage. On the next user turn, the user can answer; the agent then continues (e.g. send_email or done_tool).
3. **done_tool:** When the LLM has completed the request (e.g. sent the email), it calls **done_tool(summary="...")** or **done_tool()**. The return value is appended as a ToolMessage. **_should_continue** sees no further tool_calls in the last message, so the next node is **persist_messages** → END.
4. Neither tool calls external APIs; they only produce strings that become part of the message history and guide the agent’s and user’s next steps.

---

## 6. Related files

- **Tool list:** `src/email_assistant/tools/__init__.py` (**get_tools** imports **question_tool**, **done_tool** from here).
- **Response subgraph:** `src/email_assistant/simple_agent.py` (**bind_tools(tools)**, **ToolNode(tools)** use the list that includes these tools).
- **Agent prompt:** `src/email_assistant/prompts.py` (**get_agent_system_prompt_with_tools** tells the model when to use **question_tool** and **done_tool**).

For the tool list and get_tools, see **docs/code-explanations/tools_init.md**. For the chat/tool loop, see **docs/code-explanations/simple_agent.md**.
