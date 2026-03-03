# Explanation: `fixtures/mock_emails.py`

Detailed walkthrough of **mock email_input** payloads used for local runs, tests, and HITL demos without the Gmail API. Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–7)

```python
"""
Mock email_input payloads for local/testing and HITL demos.

Use cases: test triage (ignore/notify/respond) and interrupt/resume without Gmail API.
Each fixture is a dict suitable for graph input as email_input; optional "id" for tests
that need email_id (mark_as_read will no-op for non-Gmail ids).
"""
```

- **Line 2:** This module defines **mock email_input** payloads: dicts that look like a single email and can be passed as **email_input** when invoking the graph.
- **Lines 4–5:** **Use cases:** Test triage (ignore / notify / respond) and HITL (interrupt and resume) locally without calling the Gmail API. Scripts (e.g. **run_mock_email.py**) or tests pass **{"email_input": mock_email}** as graph input.
- **Lines 5–6:** Each fixture is a **dict** in the shape **input_router** expects (e.g. **from**, **to**, **subject**, **body**). An optional **"id"** can be set so **email_id** is present in state (e.g. for **prepare_messages** and **mark_as_read_node**); **mark_as_read** will no-op for non-Gmail ids (mock ids don’t exist in Gmail).

---

## 2. `MOCK_EMAIL_NOTIFY` (lines 9–16)

```python
# Likely classified as notify: FYI / reminder style so triage hits interrupt.
MOCK_EMAIL_NOTIFY = {
    "from": "deploy-bot@company.com",
    "to": "me@example.com",
    "subject": "FYI: deploy finished",
    "body": "Reminder: Production deploy completed at 14:00 UTC. No action required.",
    "id": "mock-notify-1",
}
```

- **Purpose:** A mock email that the triage model will likely classify as **notify** (FYI / reminder, no explicit request to reply or act). Used to exercise the path: triage → **notify** → **triage_interrupt_handler** → **interrupt()** → user resumes with respond/ignore.
- **from / to / subject / body:** Standard fields. **input_router._normalize_email_input** accepts this flat shape and leaves it as-is (adds **_source** only when it looks like Gmail; mock id is set so you can still have **email_id** in state).
- **id:** **"mock-notify-1"** so **state["email_id"]** is set. **mark_as_read_node** will call the Gmail tool with this id; the API will fail or no-op for a non-existent id, and the node catches exceptions so the graph still completes. Tests or demos that need to avoid Gmail calls can stub **mark_as_read** or rely on this no-op/fail-safe behavior.

---

## 3. `MOCK_EMAIL_RESPOND` (lines 18–25)

```python
# Clearly asks for a reply.
MOCK_EMAIL_RESPOND = {
    "from": "colleague@company.com",
    "to": "me@example.com",
    "subject": "Can you send me the report by Friday?",
    "body": "Hi, could you send me the Q4 report by end of Friday? Thanks.",
    "id": "mock-respond-1",
}
```

- **Purpose:** A mock email that clearly asks for a reply or action (“send me the report”, “by Friday”). The triage model (or **_is_explicit_request** in **triage.py**) should classify it as **respond**, so the flow goes: triage → **respond** → **prepare_messages** → response_agent (and optionally **mark_as_read**). Good for testing the full reply path without Gmail.
- **subject / body:** Phrasing chosen to trigger **respond** (and optionally **_is_explicit_request** patterns like “send me the”, “by Friday”, “the report”).
- **id:** **"mock-respond-1"** so **email_id** is set for **prepare_messages** and **mark_as_read**; **send_email_tool** with this id would call **send_reply_email** (Gmail API would fail for a fake id; tests or demos can stub the tool or accept the error).

---

## 4. `MOCK_EMAIL_IGNORE` (lines 27–33)

```python
# Low-priority; likely classified as ignore.
MOCK_EMAIL_IGNORE = {
    "from": "newsletter@marketing.com",
    "to": "me@example.com",
    "subject": "Weekly digest: top stories",
    "body": "You're receiving this because you signed up for our newsletter. Unsubscribe here.",
    "id": "mock-ignore-1",
}
```

- **Purpose:** A mock email that the triage model will likely classify as **ignore** (newsletter / marketing, no direct request). Flow: triage → **ignore** → Email Assistant subgraph ends → **_after_email_assistant_route** → **END** (no **prepare_messages**, no response_agent). Used to test the “do nothing” path.
- **from / subject / body:** Newsletter-style content so the model (and **DEFAULT_TRIAGE_INSTRUCTIONS**) treat it as low-priority / ignore.
- **id:** **"mock-ignore-1"** for consistency; on the ignore path we typically don’t run **mark_as_read** (we never reach that node), but if state is inspected in tests, **email_id** can still be present.

---

## 5. `MOCK_EMAILS` (lines 35–39)

```python
MOCK_EMAILS = {
    "notify": MOCK_EMAIL_NOTIFY,
    "respond": MOCK_EMAIL_RESPOND,
    "ignore": MOCK_EMAIL_IGNORE,
}
```

- **Purpose:** Map short names (**notify**, **respond**, **ignore**) to the three fixtures. Used by **get_mock_email(name)** so callers can request a fixture by name (e.g. from env **MOCK_EMAIL=respond** or CLI flag).

---

## 6. `get_mock_email` (lines 42–49)

```python
def get_mock_email(name: str):
    """
    Return a mock email_input by name (notify, respond, ignore).

    Use cases: run_mock_email.py or tests select fixture by env or CLI.
    """
    return MOCK_EMAILS.get(name.strip().lower(), MOCK_EMAIL_NOTIFY)
```

- **Purpose:** Return one of the mock **email_input** dicts by **name**. Used by **run_mock_email.py** or tests to choose a fixture from env (e.g. **MOCK_EMAIL=respond**) or CLI without hard-coding the dict.
- **name:** Case-insensitive key: **"notify"**, **"respond"**, or **"ignore"**. **.strip().lower()** normalizes input.
- **MOCK_EMAILS.get(..., MOCK_EMAIL_NOTIFY):** If **name** is not a key (e.g. typo or empty), return **MOCK_EMAIL_NOTIFY** as a default so the script still gets a valid **email_input** (notify path is a common demo for HITL).

---

## 7. Flow summary

1. **run_mock_email.py** (or similar) reads a fixture name (env or CLI), calls **get_mock_email(name)**, and invokes the graph with **input={"email_input": get_mock_email(name)}** (and optionally **thread_id**, **configurable**, etc.). No Gmail API is needed; **input_router** normalizes the dict and the graph runs triage and optionally response/HITL.
2. **notify** → triage returns notify → **triage_interrupt_handler** → **interrupt()**; user resumes with respond/ignore. **respond** → triage returns respond → **prepare_messages** → response_agent (and **mark_as_read** with mock id). **ignore** → triage returns ignore → subgraph ends → END.
3. Mock **id** values (e.g. **mock-notify-1**) set **state["email_id"]** so **prepare_messages** and **mark_as_read_node** run; **mark_as_read** will no-op or fail safely for non-Gmail ids. Tests can stub Gmail tools or rely on exception handling in the node.

---

## 8. Related files

- **Input router:** `src/email_assistant/nodes/input_router.py` (**_normalize_email_input** accepts these flat dicts; may set **_source** if id looks like Gmail, but mock ids are fine).
- **Triage:** `src/email_assistant/nodes/triage.py` (classifies body/subject; **_is_explicit_request** may force **respond** for **MOCK_EMAIL_RESPOND**).
- **Scripts:** **run_mock_email.py** (or equivalent) uses **get_mock_email** and invokes the graph with **email_input**.
- **StateInput:** `src/email_assistant/schemas.py` (**email_input** is an optional dict in graph input).

For how **email_input** is normalized and used, see **docs/code-explanations/nodes_input_router.md**. For triage and routing, see **docs/code-explanations/nodes_triage.md** and **docs/code-explanations/email_assistant_hitl_memory_gmail.md**.
