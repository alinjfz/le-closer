"""CLI entry for the Le Closer Meet bot.

Usage:
  python -m bot.run --meet-url https://meet.google.com/aaa-bbbb-ccc --call-id call_x
  python -m bot.run --create-space --call-id call_x      # create a Meet space via API, then join
  python -m bot.run --demo --call-id call_x               # simulated join (no browser)
  python -m bot.run --create-call --meet-url ...          # create call in backend, then join
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

from bot.meet_api import MeetAPIUnavailable, create_space, meeting_code_from_url
from bot.meet_bot import BACKEND, run_bot, run_demo


async def create_call(meet_url: str | None, demo: bool) -> str:
    async with httpx.AsyncClient() as c:
        res = await c.post(f"{BACKEND}/calls", json={
            "client": {"company": "Müller Logistik GmbH", "country": "DE",
                       "people": [{"name": "Dr. Anna Weber", "title": "Head of IT"}]},
            "mode": "sales", "demo": demo, "meet_url": meet_url,
        })
        return res.json()["call_id"]


async def main() -> None:
    p = argparse.ArgumentParser(description="Le Closer Meet bot")
    p.add_argument("--meet-url", help="Google Meet link to join")
    p.add_argument("--create-space", action="store_true", help="create a new Meet space via Meet API v2, then join it")
    p.add_argument("--call-id", help="existing Le Closer call id")
    p.add_argument("--create-call", action="store_true", help="create the call in the backend first")
    p.add_argument("--demo", action="store_true", help="simulated join — no browser, plays the demo script")
    p.add_argument("--delay", type=float, default=2.5, help="demo script delay between lines (s)")
    args = p.parse_args()

    meet_url = args.meet_url
    if args.create_space:
        try:
            space = create_space()
            meet_url = space.meeting_uri
            print(f"created Meet space: {space.meeting_uri} (code {space.meeting_code})")
        except MeetAPIUnavailable as e:
            print(f"Meet API unavailable: {e}")
            sys.exit(2)

    call_id = args.call_id
    if args.create_call or not call_id:
        call_id = await create_call(meet_url, demo=args.demo)
        print(f"created call: {call_id}")

    if args.demo:
        await run_demo(call_id, delay=args.delay)
    else:
        if not meet_url:
            print("error: pass --meet-url or --create-space (or --demo)")
            sys.exit(2)
        print(f"joining {meet_url} as Le Closer Bot for call {call_id} …")
        await run_bot(meet_url, call_id)


if __name__ == "__main__":
    asyncio.run(main())
