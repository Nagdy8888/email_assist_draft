# Explanation: `tools/gmail/prompt_templates.py`

Detailed walkthrough of **Gmail tool prompt text** for the response agent: the “Tools” section that describes **send_email_tool**, **question_tool**, and **done_tool**, plus today’s date and usage rules. Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–6)

```python
"""
GMAIL_TOOLS_PROMPT and other Gmail-related prompt snippets for the response agent.

Use cases: system prompt text describing how to use send_email (reply vs new email),
fetch_emails, and calendar tools.
"""
```

- **Line 2:** This module provides **GMAIL_TOOLS_PROMPT** (and related snippets): the Gmail-related text that is appended to the response agent’s system prompt.
- **Lines 4–5:** **Use cases:** The text describes how to use **send_email** (new email vs reply with **email_id**), and can be extended for **fetch_emails** and calendar tools. The main consumer is **get_agent_system_prompt_with_tools()** and **get_agent_system_prompt_hitl_memory()** in **prompts.py**, which call **get_gmail_tools_prompt()** and append the result to the agent’s system message.

---

## 2. Import (line 8)

```python
from datetime import datetime
```

- **datetime:** Used in **get_gmail_tools_prompt()** to get **today’s date** in **YYYY-MM-DD** format and inject it into the prompt so the agent knows the current date (e.g. for “by Friday” or scheduling). Uses **datetime.utcnow()** for a consistent reference.

---

## 3. `get_gmail_tools_prompt` (lines 10–22)

**Purpose:** Return the “Tools” section string for the response agent’s system prompt. Includes a **## Tools** heading, descriptions of **send_email_tool**, **question_tool**, and **done_tool**, today’s date, and rules (don’t invent addresses/content; when to use **email_id**). Called by **prompts.get_agent_system_prompt_with_tools()** and **get_agent_system_prompt_hitl_memory()** so the full system prompt = role + tool usage + this block.

```python
def get_gmail_tools_prompt() -> str:
    """Return the tools section for the agent system prompt (includes today's date)."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
```

- **Returns:** A single string (multi-line) that is concatenated with the rest of the system prompt in **prompts.py**.
- **today:** Current date in UTC, formatted as **YYYY-MM-DD**, so the prompt can say “Today’s date is {today}” and the model has a fixed reference date.

```python
    return f"""## Tools
- **send_email_tool**: Send an email. For a NEW email to a specific recipient, call with:
  - email_address: recipient email
  - subject: subject line
  - body: body text
  Do not pass email_id when sending a new email.
  For REPLIES to an existing email (when the user says "reply to this email" or the context is a specific email), call with email_address, subject, body, AND email_id (the Gmail message id of the email you are replying to). Use this when the user says e.g. "send an email to X" or "reply to this email".
- **question_tool**: Ask the user for clarification when you need more info (e.g. recipient, subject).
- **done_tool**: Call when you have finished the request (e.g. after sending the email).

Today's date is {today}. Do not invent email addresses or content. When the user asks to send an email to a specific address, use send_email_tool with that address, subject, and body. When replying to an email in context, include the email_id argument."""
```

- **## Tools:** Section heading so the model sees a clear “tools” block in the system prompt.
- **send_email_tool:**  
  - **NEW email:** Use **email_address**, **subject**, **body**; **do not pass email_id**.  
  - **REPLIES:** When the user says “reply to this email” or the context is a specific email, also pass **email_id** (the Gmail message id). Examples: “send an email to X” (new) vs “reply to this email” (reply with **email_id**). This aligns with **send_email.py** (if **email_id** → **send_reply_email**, else **send_new_email**) and with **prepare_messages** (injects “Use send_email_tool with email_id='...' to send your reply”).
- **question_tool:** Ask the user for clarification when needed (e.g. recipient, subject).
- **done_tool:** Call when the request is finished (e.g. after sending the email).
- **Today’s date is {today}:** Injects the current date so the model can reason about “today”, “by Friday”, etc.
- **Do not invent email addresses or content:** Reduces hallucination of recipients or body text.
- **When the user asks to send an email to a specific address, use send_email_tool with that address, subject, and body:** Reinforces using the tool with the user-provided address.
- **When replying to an email in context, include the email_id argument:** Reinforces that replies must pass **email_id** (from the injected reply context in **prepare_messages**).

---

## 4. `GMAIL_TOOLS_PROMPT` (line 24)

```python
GMAIL_TOOLS_PROMPT = get_gmail_tools_prompt()
```

- **GMAIL_TOOLS_PROMPT:** A module-level constant set to the return value of **get_gmail_tools_prompt()** at **import time**. So it is fixed to the date at import; any code that imports **GMAIL_TOOLS_PROMPT** directly gets that snapshot. **prompts.py** uses **get_gmail_tools_prompt()** (the function), not this constant, so each time the system prompt is built the date is fresh. The constant is useful if something needs the same string without calling the function (e.g. tests or a single prompt build at startup). If callers always use **get_gmail_tools_prompt()**, the constant is redundant but keeps a named export for the “static” version.

---

## 5. Flow summary

1. **prompts.get_agent_system_prompt_with_tools()** (and **get_agent_system_prompt_hitl_memory()**) call **get_gmail_tools_prompt()** and append the result to the agent system prompt. So the response agent’s system message = role + “when to use send_email / question / done” + this Tools section (with current date).
2. **get_gmail_tools_prompt()** builds the string with **datetime.utcnow()** so “Today’s date” is current each time the prompt is built (e.g. on each chat node invocation if the prompt is built per call).
3. The Tools section tells the model: new email = email_address, subject, body, no **email_id**; reply = add **email_id**; use **question_tool** for clarification; use **done_tool** when finished; don’t invent addresses or content; include **email_id** when replying to an email in context.
4. **GMAIL_TOOLS_PROMPT** is the same text evaluated once at import; most usage goes through **get_gmail_tools_prompt()** for an up-to-date date.

---

## 6. Related files

- **Agent prompts:** `src/email_assistant/prompts.py` (**get_agent_system_prompt_with_tools**, **get_agent_system_prompt_hitl_memory** call **get_gmail_tools_prompt()** and append it to the system prompt).
- **Response subgraph:** `src/email_assistant/simple_agent.py` (**_chat_node** uses **get_agent_system_prompt_with_tools()**, which includes this tools section).
- **Send email tool:** `src/email_assistant/tools/gmail/send_email.py` (**send_email_tool** behavior: new vs reply with **email_id**).
- **Tool list:** `src/email_assistant/tools/__init__.py` (**get_tools** returns send_email_tool, question_tool, done_tool — same set described here).

For the full agent prompt and where this block is used, see **docs/code-explanations/prompts.md**. For the chat node and tool loop, see **docs/code-explanations/simple_agent.md**.
