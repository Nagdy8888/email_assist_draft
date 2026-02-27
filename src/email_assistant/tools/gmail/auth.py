"""
Gmail API credentials and service builder.

Use cases: load OAuth token from GOOGLE_TOKEN_PATH; run OAuth flow if missing/expired;
build Gmail API service for send_email and (later) mark_as_read, fetch_emails.
"""

import json
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail send scope; add gmail.readonly / gmail.modify later for fetch/mark_as_read
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def _project_root() -> Path:
    """Project root (directory containing src/email_assistant). Resolves relative paths so LangSmith/langgraph dev finds .secret/."""
    # auth.py is at .../src/email_assistant/tools/gmail/auth.py -> parents[4] = project root
    return Path(__file__).resolve().parents[4]


def _resolve_path(path: str) -> str:
    """If path is relative, resolve against project root so it works when cwd is not project root (e.g. LangSmith)."""
    p = Path(path)
    if not p.is_absolute():
        p = _project_root() / path
    return str(p)


def _token_path() -> str:
    return _resolve_path(os.getenv("GOOGLE_TOKEN_PATH", ".secrets/token.json"))


def _credentials_path() -> str:
    return _resolve_path(os.getenv("GOOGLE_CREDENTIALS_PATH", ".secrets/credentials.json"))


def get_credentials() -> Credentials:
    """
    Load credentials from token.json; run OAuth flow if missing or expired.

    Use cases: call before building Gmail service. On first run, ensure
    .secrets/credentials.json exists (from Google Cloud Console) so the flow can open
    a browser and save .secrets/token.json.
    """
    token_path = _token_path()
    creds = None
    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            data = json.load(f)
        creds = Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            scopes=data.get("scopes", SCOPES),
        )
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            Path(token_path).parent.mkdir(parents=True, exist_ok=True)
            with open(token_path, "w") as f:
                json.dump(
                    {
                        "token": creds.token,
                        "refresh_token": creds.refresh_token,
                        "token_uri": creds.token_uri,
                        "client_id": creds.client_id,
                        "client_secret": creds.client_secret,
                        "scopes": creds.scopes,
                    },
                    f,
                    indent=2,
                )
        else:
            cred_path = _credentials_path()
            if not os.path.exists(cred_path):
                raise FileNotFoundError(
                    f"Credentials not found at {cred_path}. "
                    "Download OAuth client secrets from Google Cloud Console, save as "
                    ".secret/credentials.json (or .secrets/credentials.json) in the project root, then run again."
                )
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
            creds = flow.run_local_server(port=0)
        Path(token_path).parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w") as f:
            json.dump(
                {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": creds.scopes,
                },
                f,
                indent=2,
            )
    return creds


def get_gmail_service():
    """
    Return a Gmail API v1 service instance using get_credentials().

    Use cases: pass to send_new_email() or other Gmail tool functions.
    """
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds)
