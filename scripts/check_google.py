"""Check Google Meet/Calendar API access with GOOGLE_APPLICATION_CREDENTIALS.

Run:  python scripts/check_google.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if not cred:
    print("FAIL: GOOGLE_APPLICATION_CREDENTIALS is not set.")
    print("      Create OAuth client (Desktop) or service account in Google Cloud Console,")
    print("      download the JSON, and:  export GOOGLE_APPLICATION_CREDENTIALS=/path/key.json")
    sys.exit(1)
if not os.path.exists(cred):
    print(f"FAIL: file not found: {cred}")
    sys.exit(1)
print("credentials file:", cred)

try:
    from bot.meet_api import create_space
    space = create_space()
    print("PASS Meet API v2 spaces.create →", space.meeting_uri)
except Exception as e:
    print("FAIL Meet API v2 spaces.create —", str(e)[:300])
    print("      Enable the Google Meet API (meet.googleapis.com) for the project and")
    print("      grant the scope https://www.googleapis.com/auth/meetings.space.created")
    sys.exit(1)
