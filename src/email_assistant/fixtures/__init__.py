"""
Fixtures for testing and demos (mock emails, etc.).

Use cases: provide mock email_input payloads for HITL/interrupt testing without Gmail API.
"""

from email_assistant.fixtures.mock_emails import (
    MOCK_EMAIL_IGNORE,
    MOCK_EMAIL_NOTIFY,
    MOCK_EMAIL_RESPOND,
    MOCK_EMAILS,
    get_mock_email,
)

__all__ = [
    "MOCK_EMAIL_IGNORE",
    "MOCK_EMAIL_NOTIFY",
    "MOCK_EMAIL_RESPOND",
    "MOCK_EMAILS",
    "get_mock_email",
]
