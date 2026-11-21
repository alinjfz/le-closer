"""Google Meet integration — Meet API v2 + Calendar API v3.

Two ways to get a meeting for the bot:
  1. create_space()          → Meet API v2: creates a new Meet space, returns meetingUri
  2. create_calendar_meet()  → Calendar API: adds conferenceData to a calendar event

Requires a Google Cloud project with Meet/Calendar APIs enabled and a service
account (or OAuth client) in GOOGLE_APPLICATION_CREDENTIALS.

Without credentials this module raises MeetAPIUnavailable and the caller falls
back to a user-pasted Meet link or demo mode.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

SCOPES = [
    "https://www.googleapis.com/auth/meetings.space.created",
    "https://www.googleapis.com/auth/calendar.events",
]


class MeetAPIUnavailable(RuntimeError):
    pass


@dataclass
class MeetSpace:
    name: str            # "spaces/AAAA-BBBB-CCC"
    meeting_uri: str     # "https://meet.google.com/aaa-bbbb-ccc"
    meeting_code: str    # "aaa-bbbb-ccc"


def _creds():
    """Support both service-account JSON and OAuth client (installed/web) JSON.
    OAuth flow caches tokens in GOOGLE_TOKEN_FILE (default ./google_token.json);
    the first call runs the browser consent flow once."""
    import json

    path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not path or not os.path.exists(path):
        raise MeetAPIUnavailable("GOOGLE_APPLICATION_CREDENTIALS not set — point it at your client JSON.")
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        data = json.load(open(path))
        if data.get("type") == "service_account":
            return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)

        # OAuth client secret (installed/web) — interactive flow with cached token
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials as UserCredentials

        token_file = os.getenv("GOOGLE_TOKEN_FILE", os.path.join(os.path.dirname(path), "google_token.json"))
        if os.path.exists(token_file):
            creds = UserCredentials.from_authorized_user_file(token_file, SCOPES)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            if creds.valid:
                return creds
        # InstalledAppFlow expects an "installed" key; re-key a "web" client to it
        # (localhost redirect works the same)
        cfg = json.load(open(path))
        if "installed" not in cfg and "web" in cfg:
            cfg = {"installed": cfg["web"]}
            tmp = path + ".installed.json"
            with open(tmp, "w") as f:
                json.dump(cfg, f)
            path = tmp
        flow = InstalledAppFlow.from_client_secrets_file(path, scopes=SCOPES)
        creds = flow.run_local_server(port=8080, prompt="consent")
        with open(token_file, "w") as f:
            f.write(creds.to_json())
        return creds
    except ImportError as e:
        raise MeetAPIUnavailable(f"google auth libs not installed: {e}")


def create_space() -> MeetSpace:
    """Create a fresh Meet space via Meet API v2."""
    try:
        from googleapiclient.discovery import build
    except ImportError as e:
        raise MeetAPIUnavailable(f"google-api-python-client not installed: {e}")
    service = build("meet", "v2", credentials=_creds(), static_discovery=True)
    space = service.spaces().create(body={}).execute()
    return MeetSpace(
        name=space["name"],
        meeting_uri=space.get("meetingUri", ""),
        meeting_code=space.get("meetingCode", ""),
    )


def create_calendar_meet(summary: str = "Le Closer — sales call", start_iso: str | None = None) -> MeetSpace:
    """Create a Calendar event with a Meet conference attached."""
    try:
        from googleapiclient.discovery import build
    except ImportError as e:
        raise MeetAPIUnavailable(f"google-api-python-client not installed: {e}")
    from datetime import datetime, timedelta, timezone

    start = start_iso or datetime.now(timezone.utc).isoformat()
    end = (datetime.fromisoformat(start) + timedelta(hours=1)).isoformat()
    service = build("calendar", "v3", credentials=_creds(), static_discovery=True)
    event = service.events().insert(
        calendarId="primary",
        conferenceDataVersion=1,
        body={
            "summary": summary,
            "start": {"dateTime": start},
            "end": {"dateTime": end},
            "conferenceData": {
                "createRequest": {"requestId": "le-closer-bot", "conferenceSolutionKey": {"type": "hangoutsMeet"}}
            },
        },
    ).execute()
    uri = event["conferenceData"]["entryPoints"][0]["uri"]
    code = uri.rsplit("/", 1)[-1]
    return MeetSpace(name=event["id"], meeting_uri=uri, meeting_code=code)


def meeting_code_from_url(url: str) -> str:
    """Extract 'aaa-bbbb-ccc' from any Meet URL."""
    return url.rstrip("/").rsplit("/", 1)[-1]
