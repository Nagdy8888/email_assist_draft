"""
check_calendar_tool and schedule_meeting_tool via Google Calendar API.

Use cases: "What's on my calendar?" and scheduling meetings from email or user request.
"""

from datetime import datetime, timedelta
from typing import Optional

from langchain_core.tools import tool

from email_assistant.tools.gmail.auth import get_credentials


def get_calendar_service():
    """
    Return a Google Calendar API v3 service instance using shared OAuth credentials.

    Use cases: pass to list_events and create_event. Requires Calendar scope in auth.
    """
    from googleapiclient.discovery import build
    creds = get_credentials()
    return build("calendar", "v3", credentials=creds)


def list_events(
    time_min: Optional[datetime] = None,
    time_max: Optional[datetime] = None,
    max_results: int = 20,
    calendar_id: str = "primary",
) -> list[dict]:
    """
    List calendar events in the given time range.

    Use cases: check_calendar_tool calls this; agent answers "What's on my calendar tomorrow?"
    """
    service = get_calendar_service()
    params = {
        "calendarId": calendar_id,
        "singleEvents": True,
        "orderBy": "startTime",
        "maxResults": max_results,
    }
    if time_min is not None:
        params["timeMin"] = time_min.isoformat() + "Z" if time_min.tzinfo is None else time_min.isoformat()
    if time_max is not None:
        params["timeMax"] = time_max.isoformat() + "Z" if time_max.tzinfo is None else time_max.isoformat()
    result = service.events().list(**params).execute()
    return result.get("items", [])


def create_event(
    summary: str,
    start: datetime,
    end: datetime,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[list[str]] = None,
    calendar_id: str = "primary",
) -> dict:
    """
    Create a calendar event.

    Use cases: schedule_meeting_tool calls this; agent creates meetings from user or email request.
    """
    service = get_calendar_service()
    body = {
        "summary": summary,
        "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
    }
    if description:
        body["description"] = description
    if location:
        body["location"] = location
    if attendees:
        body["attendees"] = [{"email": e} for e in attendees]
    return service.events().insert(calendarId=calendar_id, body=body).execute()


def _parse_date(s: str) -> datetime:
    """Parse ISO date or datetime string to naive UTC datetime."""
    s = (s or "").strip()
    if not s:
        return datetime.utcnow()
    try:
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None) + timedelta(seconds=dt.utcoffset().total_seconds())
        return dt
    except Exception:
        return datetime.utcnow()


@tool
def check_calendar_tool(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_results: int = 20,
) -> str:
    """
    List calendar events between start_date and end_date. Dates in YYYY-MM-DD or ISO format.
    Use for questions like "What's on my calendar tomorrow?" or "Do I have meetings this week?"
    """
    time_min = _parse_date(start_date) if start_date else datetime.utcnow()
    time_max = _parse_date(end_date) if end_date else time_min + timedelta(days=7)
    if time_max <= time_min:
        time_max = time_min + timedelta(days=1)
    try:
        events = list_events(time_min=time_min, time_max=time_max, max_results=max_results)
    except Exception as e:
        return f"Failed to list calendar events: {e}"
    if not events:
        return "No events found in the given range."
    lines = []
    for e in events:
        start = e.get("start") or {}
        dt = start.get("dateTime") or start.get("date", "")
        summary = e.get("summary", "(no title)")
        lines.append(f"- {dt}: {summary}")
    return "\n".join(lines)


@tool
def schedule_meeting_tool(
    summary: str,
    start_time: str,
    end_time: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[str] = None,
) -> str:
    """
    Create a calendar event. start_time and end_time in ISO format (e.g. 2025-02-25T14:00:00).
    attendees: comma-separated email addresses.
    """
    start = _parse_date(start_time)
    end = _parse_date(end_time)
    if end <= start:
        end = start + timedelta(hours=1)
    attendee_list = [a.strip() for a in (attendees or "").split(",") if a.strip()]
    try:
        created = create_event(
            summary=summary,
            start=start,
            end=end,
            description=description,
            location=location,
            attendees=attendee_list if attendee_list else None,
        )
        return f"Event created: {created.get('htmlLink', created.get('id', 'ok'))}"
    except Exception as e:
        return f"Failed to create event: {e}"
