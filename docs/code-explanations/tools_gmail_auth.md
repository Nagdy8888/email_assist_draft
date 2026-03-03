# Explanation: `tools/gmail/auth.py`

Detailed walkthrough of **Gmail API authentication**: OAuth token path resolution, credential loading/refresh, and the Gmail service builder. Every snippet in the file is explained below.

---

## 1. Module docstring (lines 1–7)

```python
"""
Gmail API credentials and service builder.

Use cases: load OAuth token from GOOGLE_TOKEN_PATH; run OAuth flow if missing/expired;
build Gmail API service for send_email and (later) mark_as_read, fetch_emails.
"""
```

- **Line 2:** This module handles **Gmail API credentials** and provides a **service** instance (built with the Google API client library).
- **Lines 4–5:** **Use cases:** Load the OAuth token from **GOOGLE_TOKEN_PATH** (default `.secrets/token.json`); if the token is missing or expired, run the OAuth flow (browser) and save a new token; build the Gmail API service used by **send_email**, **mark_as_read**, and (later) **fetch_emails**.

---

## 2. Imports (lines 9–16)

```python
import json
import os
from pathlib import Path
```

- **json:** Read and write token/credentials files (JSON).
- **os:** Check file existence (**os.path.exists**), read env vars (**os.getenv**).
- **Path:** Resolve paths and compute project root from **__file__**; create token directory with **mkdir(parents=True, exist_ok=True)**.

```python
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
```

- **Credentials:** Google OAuth2 credentials (access token, refresh token, client id/secret, scopes). Used to load from token.json and to refresh when expired.
- **Request:** Used by **creds.refresh(Request())** to obtain a new access token using the refresh token.
- **InstalledAppFlow:** Runs the “installed application” OAuth flow (opens a browser for the user to sign in). **from_client_secrets_file** loads the client secrets (credentials.json); **run_local_server(port=0)** starts a local redirect server and opens the browser.
- **build:** Constructs a Gmail API v1 service object from the **gmail** API name, version **v1**, and **credentials**. The returned object is used to call **users().messages().send()**, **modify()**, etc.

---

## 3. `SCOPES` (lines 18–23)

```python
# Gmail send scope; gmail.readonly + gmail.modify for reply (get message/thread) and mark_as_read.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]
```

- **SCOPES:** OAuth2 scopes requested from the user. The app needs:
  - **gmail.send** — Send emails on the user’s behalf.
  - **gmail.readonly** — Read message metadata and body (for triage, fetch, reply context).
  - **gmail.modify** — Modify labels (e.g. mark as read) and possibly update messages.
- These are passed to **InstalledAppFlow** and stored in the token so refresh tokens are scoped correctly. If you add or change scopes, users may need to re-authorize (new token).

---

## 4. `_project_root` (lines 26–29)

```python
def _project_root() -> Path:
    """Project root (directory containing src/email_assistant). Resolves relative paths so LangSmith/langgraph dev finds .secret/."""
    # auth.py is at .../src/email_assistant/tools/gmail/auth.py -> parents[4] = project root
    return Path(__file__).resolve().parents[4]
```

- **Purpose:** Return the **project root** directory (the folder that contains **src/email_assistant**). Used so that relative paths like **.secrets/token.json** are resolved against the project root, not the current working directory. That way paths work when the process is started from LangSmith, LangGraph dev server, or a different cwd.
- **Path(__file__).resolve():** Absolute path of **auth.py** (e.g. **.../src/email_assistant/tools/gmail/auth.py**).
- **.parents[4]:** Go up four levels: auth.py → gmail → tools → email_assistant → src → **project root**. So the project root is the directory that contains **src**.
- **Note:** The docstring mentions “.secret/”; the default path used in code is **.secrets/** (see **_token_path**).

---

## 5. `_resolve_path` (lines 32–37)

```python
def _resolve_path(path: str) -> str:
    """If path is relative, resolve against project root so it works when cwd is not project root (e.g. LangSmith)."""
    p = Path(path)
    if not p.is_absolute():
        p = _project_root() / path
    return str(p)
```

- **Purpose:** Turn a path (from env or default) into an absolute path. If **path** is relative (e.g. **.secrets/token.json**), it is resolved against **_project_root()** so the same file is found regardless of current working directory.
- **p = Path(path):** Path object for the given string.
- **if not p.is_absolute():** Only change relative paths. Absolute paths (e.g. **/home/user/.secrets/token.json**) are returned as-is (converted to string at the end).
- **p = _project_root() / path:** Resolve relative path against project root.
- **return str(p):** Return the final path as a string for **open()** and **os.path.exists()**.

---

## 6. `_token_path` and `_credentials_path` (lines 39–44)

```python
def _token_path() -> str:
    return _resolve_path(os.getenv("GOOGLE_TOKEN_PATH", ".secrets/token.json"))


def _credentials_path() -> str:
    return _resolve_path(os.getenv("GOOGLE_CREDENTIALS_PATH", ".secrets/credentials.json"))
```

- **_token_path():** Path to the **OAuth token** file (access + refresh token and related fields). Default **.secrets/token.json** (relative to project root after **_resolve_path**). Override with **GOOGLE_TOKEN_PATH** (e.g. for different environments or a shared token).
- **_credentials_path():** Path to the **OAuth client secrets** file (from Google Cloud Console). Used only when running the OAuth flow (no token yet or re-auth). Default **.secrets/credentials.json**; override with **GOOGLE_CREDENTIALS_PATH**.

---

## 7. `get_credentials` (lines 46–109)

**Purpose:** Load OAuth credentials from the token file; if missing or invalid, refresh from refresh token or run the full OAuth flow (browser), then save the token. Returns a **Credentials** instance suitable for building the Gmail service.

```python
def get_credentials() -> Credentials:
    """
    Load credentials from token.json; run OAuth flow if missing or expired.

    Use cases: call before building Gmail service. On first run, ensure
    .secrets/credentials.json exists (from Google Cloud Console) so the flow can open
    a browser and save .secrets/token.json.
    """
```

- **Returns:** **Credentials** (google.oauth2.credentials.Credentials) with a valid **access token** (or refreshed).
- **Docstring:** First run or missing token requires **.secrets/credentials.json** (client secrets from Google Cloud Console); the flow will open a browser and save **.secrets/token.json**.

```python
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
```

- **token_path:** Resolved path to the token file (project-root relative or from env).
- **creds = None:** Start with no credentials.
- **if os.path.exists(token_path):** If a token file exists, load it and build **Credentials** from its fields. **Credentials(...)** takes: **token** (access token), **refresh_token**, **token_uri**, **client_id**, **client_secret**, **scopes**. Default **token_uri** and **scopes** (SCOPES) are used when the file omits them.

```python
    if not creds or not creds.valid:
```

- **creds.valid:** True when the access token is present and not expired. If we have no creds or they’re invalid, we need to refresh or run the OAuth flow.

```python
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
```

- **Refresh path:** We already have creds, they’re expired, and we have a **refresh_token**. Call **creds.refresh(Request())** to get a new access token. No browser needed.

```python
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
```

- After refresh, ensure the token directory exists (**mkdir(parents=True, exist_ok=True)**), then write the updated credentials (new **token**, same **refresh_token** and other fields) back to **token_path** so the next run uses the fresh access token.

```python
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
```

- **Else:** No creds, or creds not valid and we can’t refresh (no refresh_token or not expired in a way refresh handles). We must run the **full OAuth flow**.
- **cred_path:** Path to client secrets (credentials.json).
- **FileNotFoundError:** If that file doesn’t exist, raise with a message telling the user to download OAuth client secrets from Google Cloud Console and save as **.secrets/credentials.json** (or the path they configured).
- **InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES):** Create a flow that will request **SCOPES** using the client id/secret from **cred_path**.
- **flow.run_local_server(port=0):** Start a local HTTP server on a random port, open the browser for the user to sign in, and block until the redirect is received. Returns the new **Credentials** (with token and refresh_token).

```python
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
```

- After the OAuth flow (or after refresh in the branch above that writes the token), we ensure the token directory exists and write the full credentials to **token_path** so the next run can load from file. Then **return creds**. (Note: in the “refresh” branch we already wrote the token; the “else” branch (run_local_server) falls through to this same write block, so both paths persist the token. The code structure has the write block shared for the “run_local_server” path; the refresh path also writes inside its own block. So after either refresh or flow, we have creds and we’ve saved them, then return creds.)

---

## 8. `get_gmail_service` (lines 112–119)

```python
def get_gmail_service():
    """
    Return a Gmail API v1 service instance using get_credentials().

    Use cases: pass to send_new_email() or other Gmail tool functions.
    """
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds)
```

- **Purpose:** Return a **Gmail API v1** service object. Used by Gmail tools (e.g. **send_email**, **mark_as_read**) to call the API.
- **get_credentials():** Load or refresh credentials (token file + optional OAuth flow).
- **build("gmail", "v1", credentials=creds):** Create the service for the **gmail** API, version **v1**, with the given **Credentials**. The returned object provides **users()**, **users().messages()**, **users().messages().send()**, **modify()**, etc. Callers use this service to perform Gmail operations.

---

## 9. Flow summary

1. **Path resolution:** **_project_root()** and **_resolve_path()** make relative paths (e.g. **.secrets/token.json**) relative to the project root so they work from any cwd.
2. **get_credentials():** Load token from **_token_path()**. If valid, return it. If expired and we have a refresh_token, refresh and save token. If no valid creds, run **InstalledAppFlow** using **_credentials_path()**, then save token and return creds.
3. **get_gmail_service():** Call **get_credentials()**, then **build("gmail", "v1", credentials=creds)** and return the service. Gmail tools call **get_gmail_service()** (or equivalent) to obtain the service and then call **users().messages().send()**, **modify()**, etc.

---

## 10. Related files

- **Send email:** `src/email_assistant/tools/gmail/send_email.py` (uses Gmail service to send; typically gets it via auth).
- **Mark as read:** `src/email_assistant/tools/gmail/mark_as_read.py` (uses Gmail service to modify labels).
- **Configuration:** **GOOGLE_TOKEN_PATH**, **GOOGLE_CREDENTIALS_PATH**; see **docs/CONFIGURATION.md** or **docs/guide/06_CONFIGURATION.md** if present.

For the tools that use the Gmail service, see **docs/code-explanations/tools_init.md** and the Gmail tool modules under **tools/gmail/**.
