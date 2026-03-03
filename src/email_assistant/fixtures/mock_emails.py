"""
Mock email_input payloads for local/testing and HITL demos.

Use cases: test triage (ignore/notify/respond) and interrupt/resume without Gmail API.
Each fixture is a dict suitable for graph input as email_input; optional "id" for tests
that need email_id (mark_as_read will no-op for non-Gmail ids).
"""

# Likely classified as notify: FYI / reminder style so triage hits interrupt.
MOCK_EMAIL_NOTIFY = {
    "from": "deploy-bot@company.com",
    "to": "me@example.com",
    "subject": "FYI: deploy finished",
    "body": "Reminder: Production deploy completed at 14:00 UTC. No action required.",
    "id": "mock-notify-1",
}

# Clearly asks for a reply.
MOCK_EMAIL_RESPOND = {
    "from": "colleague@company.com",
    "to": "me@example.com",
    "subject": "Can you send me the report by Friday?",
    "body": "Hi, could you send me the Q4 report by end of Friday? Thanks.",
    "id": "mock-respond-1",
}

# Low-priority; likely classified as ignore.
MOCK_EMAIL_IGNORE = {
    "from": "newsletter@marketing.com",
    "to": "me@example.com",
    "subject": "Weekly digest: top stories",
    "body": "You're receiving this because you signed up for our newsletter. Unsubscribe here.",
    "id": "mock-ignore-1",
}

MOCK_EMAILS = {
    "notify": MOCK_EMAIL_NOTIFY,
    "respond": MOCK_EMAIL_RESPOND,
    "ignore": MOCK_EMAIL_IGNORE,
}


def get_mock_email(name: str):
    """
    Return a mock email_input by name (notify, respond, ignore).

    Use cases: run_mock_email.py or tests select fixture by env or CLI.
    """
    return MOCK_EMAILS.get(name.strip().lower(), MOCK_EMAIL_NOTIFY)
