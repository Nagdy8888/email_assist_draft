# Explanation: `nodes/triage_interrupt.py`

Detailed walkthrough of the **triage_interrupt_handler** node: when triage classified an email as **notify**, this node pauses the graph for a human choice (**respond** or **ignore**) and writes the choice into **state["_notify_choice"]**. Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–7)

```python
"""
triage_interrupt_handler: when classification is notify, pause for human choice (respond or ignore).

Use cases: after triage_router when classification is notify; calls interrupt() so the
graph pauses and the user can resume with Command(resume="respond") or Command(resume="ignore").
Requires a checkpointer (e.g. Postgres or MemorySaver) for interrupt to work.
"""
```

- **Line 2:** This module implements **triage_interrupt_handler**, which runs only when the triage result is **notify**. It pauses execution so a human can choose **respond** or **ignore**.
- **Lines 4–5:** **Use cases:** The node runs after **triage_router** when **classification_decision == "notify"**. It calls **interrupt()**, so the graph stops and state is persisted. The user (in Studio or via CLI) resumes by sending **Command(resume="respond")** or **Command(resume="ignore")**.
- **Line 6:** **interrupt()** only works if the graph was compiled with a **checkpointer** (e.g. Postgres or MemorySaver). The checkpointer saves state at the interrupt; on resume, the same thread is restored and execution continues from this node.

---

## 2. Imports (lines 9–11)

```python
from langgraph.types import interrupt
```

- **interrupt:** LangGraph’s HITL primitive. When called with a payload (e.g. a dict with message and options), the graph **pauses** and returns control to the caller. The caller later **resumes** the same thread with a **Command(resume=...)**; the value passed to **resume** is the return value of **interrupt()** when execution continues.

```python
from email_assistant.schemas import State
```

- **State:** Graph state type. The node reads state (e.g. to know we’re in the notify path) and returns **{"_notify_choice": choice}** so the parent graph can route to **prepare_messages** (respond) or **END** (ignore).

---

## 3. `NOTIFY_INTERRUPT_MESSAGE` (lines 14–19)

```python
# Payload shown to the user when the graph is waiting for respond/ignore (e.g. in Studio).
NOTIFY_INTERRUPT_MESSAGE = {
    "message": "This email was classified as **notify** (FYI). Should the assistant respond or ignore?",
    "options": ["respond", "ignore"],
}
```

- **Purpose:** The payload passed to **interrupt(...)**. It is stored with the checkpoint and shown to the user (e.g. in LangGraph Studio) so they know why the graph is waiting and what choices they have.
- **message:** Short explanation: the email was classified as **notify** (FYI) and the user must choose whether the assistant should **respond** or **ignore**.
- **options:** List of valid resume values. The UI can use this to render buttons or a dropdown; the user’s selection is sent as **Command(resume="respond")** or **Command(resume="ignore")**.

---

## 4. `triage_interrupt_handler` (lines 21–40)

**Purpose:** Pause the graph for a human decision, then normalize the resume value and write it to **state["_notify_choice"]** so the top-level conditional edge (**_after_email_assistant_route**) can route to **prepare_messages** or **END**.

```python
def triage_interrupt_handler(state: State) -> dict:
    """
    When classification is notify, pause and wait for human choice; return _notify_choice.

    Use cases: after triage_router when classification is notify. Calls interrupt() so
    the graph pauses; the caller (Studio or run_agent.py / run_mock_email.py) resumes with
    Command(resume="respond") or Command(resume="ignore"). The resume value becomes the
    return value of interrupt() and is written to _notify_choice.
    """
```

- **state:** Current graph state. The node doesn’t read specific keys here; it only returns an update. It runs only when the subgraph routed to it (because **classification_decision == "notify"**).
- **Returns:** A dict merged into state; we set **"_notify_choice"** to the normalized choice (**"respond"** or **"ignore"**).
- **Docstring:** Describes the flow: **interrupt()** pauses; caller resumes with **Command(resume="respond")** or **Command(resume="ignore")**; that value is what **interrupt()** returns when the run continues, and we write it to **_notify_choice**.

```python
    # Pause for human decision. On resume, Command(resume="respond") or Command(resume="ignore")
    # is passed here as choice.
    choice = interrupt(NOTIFY_INTERRUPT_MESSAGE)
```

- **interrupt(NOTIFY_INTERRUPT_MESSAGE):** Tells LangGraph to **pause** the run and persist state (requires a checkpointer). The **NOTIFY_INTERRUPT_MESSAGE** dict is available to the UI so the user sees the message and options.
- **First time:** When the node runs, **interrupt()** does not return immediately; the graph yields control. When the user (or test) resumes the thread with **Command(resume="respond")** or **Command(resume="ignore")**, execution continues and **interrupt()** returns that resume value.
- **choice:** The value the user chose: typically the string **"respond"** or **"ignore"**. Could be another type if the client sends something else, so we normalize below.

```python
    if isinstance(choice, str):
        choice = choice.strip().lower()
    else:
        choice = "ignore"
```

- **Normalize choice:** If **choice** is a string, we **strip** and **lower** it so we can compare with **"respond"** and **"ignore"**. If **choice** is not a string (e.g. None or a dict from a malformed client), we default to **"ignore"**.

```python
    if choice not in ("respond", "ignore"):
        choice = "ignore"
```

- **Validation:** Only **"respond"** and **"ignore"** are valid. Any other value (e.g. typo, empty string, or unknown client payload) is forced to **"ignore"** so the graph always has a valid **_notify_choice** and never gets stuck.

```python
    return {"_notify_choice": choice}
```

- Return the state update. LangGraph merges **{"_notify_choice": choice}** into state. The Email Assistant subgraph then ends (next edge is **triage_interrupt_handler → END**). The **top-level** graph runs **_after_email_assistant_route**, which reads **state["_notify_choice"]**: if **"respond"** → **prepare_messages** (then response_agent); else → **END**.

---

## 5. Flow summary

1. **triage_router** sets **classification_decision** to **"notify"**.
2. The Email Assistant subgraph’s conditional edge (**_after_triage_route**) sends control to **triage_interrupt_handler**.
3. **triage_interrupt_handler** calls **interrupt(NOTIFY_INTERRUPT_MESSAGE)** → graph pauses; state is checkpointed; user sees the message and options (e.g. in Studio).
4. User resumes with **Command(resume="respond")** or **Command(resume="ignore")**. **interrupt()** returns that value.
5. Handler normalizes and validates the value, then returns **{"_notify_choice": "respond" | "ignore"}**.
6. Subgraph exits (handler → END). Top-level **_after_email_assistant_route** sees **_notify_choice**: **respond** → **prepare_messages**; **ignore** → **END**.

---

## 6. Related files

- **State / _notify_choice:** `src/email_assistant/schemas.py` (**State** has **"_notify_choice": Optional[str]**).
- **Graph wiring:** `src/email_assistant/email_assistant_hitl_memory_gmail.py` (**build_email_assistant_subgraph**: triage_router → _after_triage_route → triage_interrupt_handler → END; **\_after_email_assistant_route** reads **_notify_choice**).
- **Checkpointer:** Required for **interrupt()**; set at compile time in **build_email_assistant_graph(checkpointer=...)** or by the LangGraph API when serving for Studio.

For the subgraph and top-level routing, see **docs/code-explanations/email_assistant_hitl_memory_gmail.md**. For state shape, see **docs/code-explanations/schemas.md**.
