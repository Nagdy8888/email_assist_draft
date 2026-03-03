# Explanation: `prompts.py`

Detailed walkthrough of the **prompt text and builders** used by the Email Assistant: triage, response agent, and notify choice. Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–6)

```python
"""
Triage, agent, and memory-update prompts; default_* constants.

Use cases: centralize system prompts for triage router, response agent, and
memory-update LLM; keep prompt text out of node code.
"""
```

- **Line 2:** This module holds all **prompt text** and **default constants** for the triage router, the response agent (with tools), and the memory-update / notify-choice flows.
- **Lines 4–5:** **Use cases:** Keep prompts in one place so the **triage router**, **response agent**, and **memory-update** LLM all get their system (and user) prompts from here instead of having long strings inside node code. Makes it easier to edit prompts and stay consistent.

---

## 2. `SIMPLE_AGENT_SYSTEM_PROMPT` (lines 8–12)

```python
# Phase 2: system prompt for the simple Q&A agent (no tools, no triage).
SIMPLE_AGENT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's questions clearly and concisely."
)
```

- **Comment:** From the phased plan, Phase 2 introduced a simple Q&A agent with no tools and no triage.
- **SIMPLE_AGENT_SYSTEM_PROMPT:** A single string used as the system message when the agent is “simple” (no send_email, no triage). Tells the LLM to answer clearly and concisely. May be used in tests, a minimal flow, or as a fallback; the main response agent uses **get_agent_system_prompt_with_tools()** instead.

---

## 3. `DEFAULT_TRIAGE_INSTRUCTIONS` (lines 14–20)

```python
# Phase 5: triage prompts and defaults.
DEFAULT_TRIAGE_INSTRUCTIONS = """## Triage categories (use exactly one)
- **ignore**: No action needed; low value or noise. Examples: marketing newsletters, automated receipts, out-of-office replies, broad announcements that do not require your response. Do NOT use ignore when the email asks the recipient to send something, reply, or take an action.
- **notify**: User should see it but no reply needed. Examples: deploy completions, HR deadline reminders, status updates, FYI items. Do NOT use notify when the subject or body explicitly asks for a document, report, or reply (e.g. "Can you send me the report by Friday?").
- **respond**: Needs a direct reply or action from the user or from the assistant. Examples: direct questions, "send me the report", "can you send me X by Friday", meeting requests, client or manager asks, anything that explicitly asks for a response, document, or action. **Always use respond** when the subject or body asks the recipient to send something, reply with information, or perform an action (e.g. "send me the report", "send this to Gmail", "reply to this", "could you send me the Q4 report") so the assistant can use its tools.

When in doubt between ignore and notify, prefer **notify**. When in doubt between notify and respond, prefer **respond** when a direct reply or action is requested. If the body or subject contains a request (e.g. "send me", "could you send", "please reply"), classify as **respond**."""
```

- **Comment:** Phase 5 added triage; these are the default instructions for the triage categories.
- **Purpose:** Defines the three labels (**ignore**, **notify**, **respond**) and when to use each so the triage LLM outputs a single, consistent classification.
- **ignore:** Low value, no action (newsletters, receipts, OOO, broad announcements). Explicit rule: do **not** use ignore when the email asks the recipient to send something, reply, or take an action.
- **notify:** User should see it but no reply needed (deploy done, reminders, FYI). Explicit rule: do **not** use notify when the email explicitly asks for a document, report, or reply (e.g. “Can you send me the report by Friday?”).
- **respond:** Direct reply or action needed; includes any request for a response, document, or action. **Always use respond** when the subject or body asks to send something, reply, or perform an action so the assistant can use tools.
- **Fallbacks:** Prefer **notify** over ignore when in doubt; prefer **respond** when a direct reply or action is requested; if the body or subject contains a request phrase (“send me”, “could you send”, “please reply”), classify as **respond**.

This string is the default passed into **get_triage_system_prompt** as **triage_instructions** when no custom instructions are provided (e.g. from memory).

---

## 4. `get_triage_system_prompt` (lines 22–39)

**Purpose:** Build the **system prompt** for the triage router LLM. Injects **background** (e.g. from memory) and **triage_instructions** (custom or **DEFAULT_TRIAGE_INSTRUCTIONS**), and adds today’s date.

```python
def get_triage_system_prompt(background: str = "", triage_instructions: str = "") -> str:
    """System prompt for triage router LLM. Injects background and triage_instructions (from memory or default)."""
```

- **background:** Optional context (e.g. user preferences or memory) inserted into the prompt. Default empty.
- **triage_instructions:** Category rules; if empty, **DEFAULT_TRIAGE_INSTRUCTIONS** is used.
- Returns one string that is sent as the **system** message to the triage LLM.

```python
    from datetime import datetime
    instructions = triage_instructions or DEFAULT_TRIAGE_INSTRUCTIONS
    today = datetime.utcnow().strftime("%Y-%m-%d")
```

- **datetime:** Used only for **today** so the model knows the current date.
- **instructions:** Use the provided **triage_instructions** or fall back to **DEFAULT_TRIAGE_INSTRUCTIONS**.
- **today:** Formatted as **YYYY-MM-DD** in UTC, injected into the prompt so the model can reason about “today” or deadlines.

```python
    return f"""You are an email triage assistant. Your task is to classify each email into exactly one of: ignore, notify, respond.

**CRITICAL:** If the subject or body asks the recipient to send something, reply, or take an action (e.g. "send me the report", "could you send me the Q4 report", "by Friday"), you MUST classify as **respond**. Do not use ignore or notify for such emails.

## Background
{background or "No specific background provided."}

When the email is from the user's Gmail inbox (incoming message just sent to them), classify whether to ignore, notify, or respond based on the content.

## Instructions
{instructions}

Today's date is {today}. You must output exactly one classification. Do not invent categories. **If the subject or body asks the recipient to send a document, report, or reply (e.g. "Can you send me the report", "could you send me the Q4 report"), always classify as respond.** If the content is the user asking the assistant to send an email or take an action, always classify as **respond**. Prefer notify over ignore when in doubt; prefer respond when a direct reply or action is requested."""
```

- **Role:** “Email triage assistant”; output exactly one of ignore, notify, respond.
- **CRITICAL block:** Reinforces that any request to send something, reply, or take an action must be **respond**, not ignore or notify.
- **## Background:** Injects **background** or “No specific background provided.” so the model can use user-specific context when available.
- **Inbox note:** Clarifies that when the email is from the user’s Gmail inbox (incoming), classification is based on content.
- **## Instructions:** Injects **instructions** (the category definitions and rules).
- **Today’s date:** **{today}** so the model has a fixed reference date.
- **Closing rules:** One classification only; no new categories; repeat “always respond when they ask for document/report/reply or for the assistant to send/take action”; prefer notify over ignore, respond when a direct reply or action is requested.

---

## 5. `get_triage_user_prompt` (lines 41–54)

**Purpose:** Build the **user prompt** for triage: the email’s metadata and body in a fixed format. Optionally states that the email just arrived in the user’s Gmail inbox.

```python
def get_triage_user_prompt(from_addr: str, to_addr: str, subject: str, body_or_thread: str, from_gmail_inbox: bool = False) -> str:
    """User prompt for triage: email metadata and content in a fixed format.
    When from_gmail_inbox is True, states that this email was just sent to the user's Gmail inbox."""
```

- **from_addr, to_addr, subject:** Email headers.
- **body_or_thread:** Full body text or thread content to classify.
- **from_gmail_inbox:** If **True**, the prompt adds a note that this email just arrived in the user’s Gmail inbox (incoming). Helps the model treat it as an incoming message to triage.

```python
    inbox_note = "\n**This email just arrived in the user's Gmail inbox (incoming message).**\n" if from_gmail_inbox else ""
    return f"""## Email to classify{inbox_note}
- **From:** {from_addr}
- **To:** {to_addr}
- **Subject:** {subject}

## Body / thread
{body_or_thread}

Classify the above email into exactly one of: ignore, notify, respond. Output your reasoning and then your classification."""
```

- **inbox_note:** Either the bold inbox line (when **from_gmail_inbox** is True) or an empty string.
- **Structure:** “## Email to classify” + optional inbox note, then From/To/Subject, then “## Body / thread” and the content.
- **Final line:** Asks for exactly one of ignore, notify, respond and to output reasoning then classification (so the triage node or parser can read the classification, e.g. for **RouterSchema**).

---

## 6. `NOTIFY_CHOICE_SYSTEM` (lines 56–61)

```python
NOTIFY_CHOICE_SYSTEM = """You are an email assistant. The previous step classified this email as "notify" (FYI - user should see it but no reply was required). Now you must decide: should the assistant **respond** to this email anyway (e.g. send a short acknowledgment or reply), or **ignore** it (no response)?

- Choose **respond** if: the content might benefit from a brief reply, acknowledgment, or the user would likely want to reply (e.g. from a colleague, contains a question, or actionable item).
- Choose **ignore** if: it is purely informational, a broadcast, or no reply adds value.

Output exactly one: respond or ignore."""
```

- **Purpose:** System prompt for the **notify** follow-up step: the email was already classified as **notify** (FYI, no reply required), and now we decide whether the assistant should **respond** anyway or **ignore**.
- **respond:** Use when a brief reply or acknowledgment could help, or the user would likely want to reply (e.g. from a colleague, has a question or actionable item).
- **ignore:** Use when it’s purely informational, a broadcast, or a reply adds no value.
- **Output:** Exactly one word: **respond** or **ignore**. This aligns with **NotifyChoiceSchema** and **state["_notify_choice"]** when the choice is made by an LLM (e.g. auto-decision path) or for structuring the user’s choice in HITL.

---

## 7. `get_notify_choice_user_prompt` (lines 64–73)

```python
def get_notify_choice_user_prompt(from_addr: str, subject: str, body_snippet: str) -> str:
    """User prompt for notify auto-decision: minimal email context."""
    return f"""Email (classified as notify):
- From: {from_addr}
- Subject: {subject}
- Body (snippet): {body_snippet}

Should the assistant respond or ignore? Answer with exactly one word: respond or ignore."""
```

- **Purpose:** Build the **user** message for the notify-choice step (auto-decision or HITL). Gives minimal context: from, subject, and a **body_snippet** (not the full body) so the model can decide respond vs ignore quickly.
- **Parameters:** **from_addr**, **subject**, **body_snippet** — enough to remind the model which email is being decided on.
- **Ask:** “Should the assistant respond or ignore? Answer with exactly one word: respond or ignore.” So the response can be parsed to set **_notify_choice** or **NotifyChoiceSchema**.

---

## 8. `get_agent_system_prompt_with_tools` (lines 75–87)

**Purpose:** Build the **system prompt** for the response agent when it has tools (send_email, question, done). Used by the main response subgraph (e.g. **_chat_node** in **simple_agent.py**).

```python
# Phase 4: system prompt for the agent with tools (send email, question, done).
def get_agent_system_prompt_with_tools() -> str:
    """System prompt for response agent with send_email_tool and question/done."""
```

- **Comment:** Phase 4 added the agent with tools (send email, question, done).
- **Returns:** One string: role + tool usage rules + Gmail-specific tool text from **get_gmail_tools_prompt()**.

```python
    from email_assistant.tools.gmail.prompt_templates import get_gmail_tools_prompt
    return (
        "You are a helpful assistant. You can send emails on the user's behalf and answer questions. "
        "When the user asks you to send an email to a specific address, use send_email_tool with "
        "email_address, subject, and body (do not use email_id for new emails). "
        "When replying to an email (e.g. 'reply to this email'), use send_email_tool with email_id as well. "
        "When you need clarification, use question_tool. When you have completed the request, use done_tool.\n\n"
        + get_gmail_tools_prompt()
    )
```

- **Role:** Helpful assistant; can send emails and answer questions.
- **New emails:** Use **send_email_tool** with **email_address**, **subject**, **body**; do **not** use **email_id** for new emails.
- **Replies:** When replying (e.g. “reply to this email”), use **send_email_tool** with **email_id** as well.
- **question_tool:** Use when clarification is needed.
- **done_tool:** Use when the request is completed.
- **get_gmail_tools_prompt():** Appends Gmail-specific instructions (e.g. labels, search, read) from **email_assistant.tools.gmail.prompt_templates**. The full system prompt is this block plus the Gmail tools section.

---

## 9. `get_agent_system_prompt_hitl_memory` (lines 89–108)

**Purpose:** Build the **system prompt** for the response agent when using **HITL and memory** (Phase 6). Adds optional **response_preferences** and **cal_preferences**, today’s date, and the same Gmail tools section. Phase 5 uses the same tools content; this function adds preference sections and date for the memory/HITL flow.

```python
# Phase 5: response agent prompt with HITL/memory placeholders (same content as get_agent_system_prompt_with_tools for now).
def get_agent_system_prompt_hitl_memory(
    response_preferences: str = "",
    cal_preferences: str = "",
) -> str:
    """System prompt for response agent when using memory (Phase 6). Phase 5 uses same tools prompt."""
```

- **Comment:** Placeholders for HITL/memory; content was initially the same as the tools-only prompt.
- **response_preferences:** Optional text from memory about how the user wants replies (injected under “## Response preferences”).
- **cal_preferences:** Optional text about calendar preferences (injected under “## Calendar preferences”).
- Used when the graph runs with memory (Phase 6); Phase 5 can still use the same tools prompt by passing empty strings.

```python
    from datetime import datetime
    from email_assistant.tools.gmail.prompt_templates import get_gmail_tools_prompt
    today = datetime.utcnow().strftime("%Y-%m-%d")
```

- **today:** Current date in **YYYY-MM-DD** (UTC) for the prompt.

```python
    prefs = f"\n## Response preferences\n{response_preferences}\n" if response_preferences else ""
    cal = f"\n## Calendar preferences\n{cal_preferences}\n" if cal_preferences else ""
```

- **prefs:** If **response_preferences** is non-empty, a “## Response preferences” section with that text; otherwise empty string.
- **cal:** If **cal_preferences** is non-empty, a “## Calendar preferences” section; otherwise empty string. So when memory is not used, these sections are omitted.

```python
    return (
        "You are an email assistant. You can send emails (new or reply), ask the user for clarification, and mark tasks done.\n"
        + prefs
        + cal
        + "\n"
        + get_gmail_tools_prompt()
        + f"\n\nToday's date is {today}. Do not invent recipients, events, or email content. When in doubt, use question_tool. Use done_tool when finished."
    )
```

- **Role:** Email assistant; can send emails (new or reply), ask for clarification, mark tasks done.
- **prefs + cal:** Injects the optional Response and Calendar preference sections.
- **get_gmail_tools_prompt():** Same Gmail tools block as in **get_agent_system_prompt_with_tools**.
- **Closing:** Today’s date; do not invent recipients, events, or email content; when in doubt use **question_tool**; use **done_tool** when finished.

---

## 10. Who uses which prompt

| Symbol | Used by |
|--------|--------|
| **SIMPLE_AGENT_SYSTEM_PROMPT** | Simple Q&A path or tests (no tools, no triage). |
| **DEFAULT_TRIAGE_INSTRUCTIONS** | **get_triage_system_prompt** when no custom **triage_instructions** are passed. |
| **get_triage_system_prompt** | Triage router node (system message). |
| **get_triage_user_prompt** | Triage router node (user message with email to classify). |
| **NOTIFY_CHOICE_SYSTEM** | Notify-choice step (system message when deciding respond vs ignore after “notify”). |
| **get_notify_choice_user_prompt** | Notify-choice step (user message with email snippet). |
| **get_agent_system_prompt_with_tools** | Response subgraph **_chat_node** in **simple_agent.py** (main agent with tools). |
| **get_agent_system_prompt_hitl_memory** | Response agent when running with memory (Phase 6); adds preferences and date. |

---

## 11. Related files

- **Triage node:** `src/email_assistant/nodes/triage.py` (uses **get_triage_system_prompt**, **get_triage_user_prompt**, **DEFAULT_TRIAGE_INSTRUCTIONS**).
- **Notify choice / HITL:** `src/email_assistant/nodes/triage_interrupt.py` (may use **NOTIFY_CHOICE_SYSTEM**, **get_notify_choice_user_prompt**).
- **Response agent:** `src/email_assistant/simple_agent.py` (**_chat_node** uses **get_agent_system_prompt_with_tools**).
- **Gmail tool text:** `src/email_assistant/tools/gmail/prompt_templates.py` (**get_gmail_tools_prompt**).

For state and routing that use triage outputs, see **docs/code-explanations/schemas.md** and **docs/code-explanations/email_assistant_hitl_memory_gmail.md**.
