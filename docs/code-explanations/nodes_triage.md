# Explanation: `nodes/triage.py`

Detailed walkthrough of the **triage_router** node: it classifies an email as **ignore**, **notify**, or **respond** using one LLM call with structured output (**RouterSchema**). Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–6)

```python
"""
triage_router: classify email as ignore / notify / respond using RouterSchema.

Use cases: single LLM call with structured output; uses triage prompts and memory.
"""
```

- **Line 2:** This module implements **triage_router**, which assigns a single label (**ignore** / **notify** / **respond**) to the current email using **RouterSchema** (structured LLM output).
- **Lines 4–5:** **Use cases:** One LLM call with structured output; uses the triage system and user prompts from **prompts.py** (and can use memory for background/instructions in the future). The result drives the conditional edges in the Email Assistant subgraph.

---

## 2. Imports (lines 8–14)

```python
import os
```

- Used to read **OPENAI_MODEL** and **OPENAI_API_KEY** when creating the ChatOpenAI client.

```python
from langchain_core.messages import HumanMessage, SystemMessage
```

- **SystemMessage:** Wraps the triage system prompt (role + instructions + background).
- **HumanMessage:** Wraps the user prompt (the email to classify: from, to, subject, body, optional inbox note).

```python
from langchain_openai import ChatOpenAI
```

- **ChatOpenAI:** LLM client for the triage call. Configured with model and API key from env.

```python
from email_assistant.prompts import get_triage_system_prompt, get_triage_user_prompt
from email_assistant.schemas import RouterSchema, State
```

- **get_triage_system_prompt:** Builds the system prompt (optional background, triage instructions, today’s date). Called with no args here, so uses defaults.
- **get_triage_user_prompt:** Builds the user prompt with email metadata and body (and optional “just arrived in Gmail inbox” note).
- **RouterSchema:** TypedDict for structured output: **reasoning** (str) and **classification** (ignore | notify | respond). The LLM is asked to return this shape.
- **State:** Graph state type; the node reads **email_input** and returns **classification_decision**.

---

## 3. `triage_router` (lines 17–48)

**Purpose:** Run the triage LLM on **state["email_input"]**, optionally skip the LLM when the email is an explicit request (override to **respond**), and return **classification_decision** for the conditional edges.

```python
def triage_router(state: State) -> dict:
    """
    Run triage LLM with structured output (RouterSchema). Return classification_decision and optionally reasoning.

    Use cases: after input_router when email_input is present; output drives conditional edges (ignore/notify/respond).
    """
```

- **state:** Current graph state; must have **email_input** set (normalized by input_router) when we’re on the email path.
- **Returns:** A dict merged into state; we only set **classification_decision** here. The subgraph’s conditional edge (**_after_triage_route**) reads it to go to **triage_interrupt_handler** (notify) or **END** (ignore/respond).

```python
    email_input = state.get("email_input")
    if not email_input:
        return {"classification_decision": "ignore"}
```

- **email_input:** Normalized email dict from **input_router** (from, to, subject, body, id, _source).
- If **email_input** is missing (shouldn’t happen on the email path, but defensive), we return **ignore** so the graph doesn’t block and the flow can end.

```python
    from_addr = email_input.get("from", "")
    to_addr = email_input.get("to", "")
    subject = email_input.get("subject", "")
    body = str(email_input.get("body", ""))[:8000]
    from_gmail_inbox = email_input.get("_source") == "gmail"
```

- **from_addr, to_addr, subject:** Passed into **get_triage_user_prompt** for the “Email to classify” section.
- **body:** Coerced to string and truncated to **8000** characters so the prompt stays within token limits while keeping the start of the email.
- **from_gmail_inbox:** True when **input_router** set **_source** to **"gmail"** (incoming Gmail message). Passed to **get_triage_user_prompt** so it can add “This email just arrived in the user’s Gmail inbox.”

```python
    # Override: if subject or body clearly asks for a reply/document/action, force respond (avoids LLM misclassification).
    if _is_explicit_request(str(subject), body):
        return {"classification_decision": "respond"}
```

- **Override:** Before calling the LLM, we check if the subject or body clearly asks for a reply, document, or action (e.g. “send me the report”, “please reply”). If **\_is_explicit_request** returns True, we skip the LLM and return **respond** so such emails are never misclassified as ignore or notify.

```python
    system = get_triage_system_prompt()
    user = get_triage_user_prompt(from_addr, to_addr, subject, body, from_gmail_inbox=from_gmail_inbox)
```

- **system:** Full triage system prompt (role, CRITICAL rules, background, instructions, today’s date). Called with no args → default background and **DEFAULT_TRIAGE_INSTRUCTIONS**.
- **user:** User message containing the email to classify (from, to, subject, body, optional inbox note). Format is fixed so the LLM and **RouterSchema** stay aligned.

```python
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )
```

- **ChatOpenAI** is configured from env: **OPENAI_MODEL** (default **gpt-4o**), **OPENAI_API_KEY**. A new client is created on each invocation.

```python
    structured = llm.with_structured_output(RouterSchema)
    result = structured.invoke([SystemMessage(content=system), HumanMessage(content=user)])
```

- **with_structured_output(RouterSchema):** Asks the LLM to return a dict that matches **RouterSchema** (reasoning, classification). LangChain/OpenAI handle the structured-output mechanism (e.g. JSON schema, parsing).
- **invoke([...]):** Single call with system then user message. **result** is a dict with keys **"reasoning"** and **"classification"**.

```python
    classification = (result.get("classification") or "ignore").strip().lower()
    if classification not in ("ignore", "notify", "respond"):
        classification = "ignore"
```

- **classification:** Read from **result["classification"]**; if missing or None, use **"ignore"**. Normalized with **.strip().lower()** for comparison.
- **Validation:** If the value isn’t one of the three allowed labels (e.g. model hallucination), we force **"ignore"** so the graph always sees a valid **ClassificationDecision**.

```python
    return {
        "classification_decision": classification,
    }
```

- Return a state update with **classification_decision** set. The parent graph and **_after_triage_route** use this to route: **notify** → triage_interrupt_handler; **ignore** or **respond** → END (then **_after_email_assistant_route** uses it to decide prepare_messages vs END).

---

## 4. `_is_explicit_request` (lines 51–74)

**Purpose:** Detect when the email clearly asks the recipient to send something, reply, or take an action. Used to force triage to **respond** without calling the LLM, avoiding misclassification of obvious requests.

```python
def _is_explicit_request(subject: str, body: str) -> bool:
    """
    True if the email clearly asks the recipient to send something, reply, or take an action.

    Use cases: force triage to "respond" for colleague requests like "send me the report by Friday"
    so the LLM cannot misclassify as ignore.
    """
```

- **subject, body:** Raw subject and body text (already truncated for body in the caller). We search for request-like phrases in the combined text.
- **Returns:** True if any of the predefined patterns appear (case-insensitive), so we can return **{"classification_decision": "respond"}** from **triage_router** without calling the LLM.

```python
    combined = f"{subject}\n{body}".lower()
```

- **combined:** One string containing subject and body in lowercase so we can do case-insensitive substring checks with the patterns below.

```python
    patterns = (
        "send me the",
        "send me a",
        "could you send",
        "can you send",
        "please send",
        "please reply",
        "reply with",
        "by friday",
        "by monday",
        "by end of",
        "q4 report",
        "the report",
    )
```

- **patterns:** Tuple of phrases that typically indicate a request for a reply, document, or action. “send me the/a”, “could/can you send”, “please send/reply”, “reply with”, deadline-like “by friday/monday/end of”, and “q4 report” / “the report” (common in “send me the report” style requests). Chosen to reduce false negatives for clear requests.

```python
    return any(p in combined for p in patterns)
```

- **any(p in combined for p in patterns):** True if at least one pattern is a substring of **combined**. So if the email clearly asks for something (e.g. “Could you send me the report by Friday?”), we return True and **triage_router** returns **respond** without calling the LLM.

---

## 5. Flow summary

1. **triage_router** runs inside the **email_assistant** subgraph after **input_router** has set **email_input**.
2. If **email_input** is missing → return **ignore** and exit.
3. Extract from/to/subject/body and **from_gmail_inbox**; truncate body to 8000 chars.
4. If **\_is_explicit_request(subject, body)** is True → return **respond** (no LLM call).
5. Otherwise: build system and user prompts, call the LLM with **RouterSchema**, read **classification**, validate it (fallback to **ignore** if invalid), return **classification_decision**.
6. The subgraph’s conditional edge uses **classification_decision**: **notify** → triage_interrupt_handler; **ignore** / **respond** → END. The top-level graph then uses **classification_decision** (and **_notify_choice** after notify) to route to **prepare_messages** or END.

---

## 6. Related files

- **State / RouterSchema:** `src/email_assistant/schemas.py` (**classification_decision**, **RouterSchema**).
- **Prompts:** `src/email_assistant/prompts.py` (**get_triage_system_prompt**, **get_triage_user_prompt**, **DEFAULT_TRIAGE_INSTRUCTIONS**).
- **Graph wiring:** `src/email_assistant/email_assistant_hitl_memory_gmail.py` (**build_email_assistant_subgraph**: START → triage_router → _after_triage_route → triage_interrupt_handler or END).
- **Input:** `src/email_assistant/nodes/input_router.py` (normalizes **email_input** and sets **_source** for Gmail).

For the subgraph flow and routing, see **docs/code-explanations/email_assistant_hitl_memory_gmail.md**. For prompts and schemas, see **docs/code-explanations/prompts.md** and **docs/code-explanations/schemas.md**.
