"""End-to-end: create call with meet link, run bot in --demo mode, verify
bot status events + the realistic script flows through the pipeline."""
import asyncio
import json
import subprocess
import sys
import time
import urllib.request

import websockets

BASE = "http://localhost:8003"


def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req).read())


def get(path):
    return json.loads(urllib.request.urlopen(BASE + path).read())


async def main():
    call = post("/calls", {
        "client": {"company": "Müller Logistik GmbH", "country": "DE",
                   "people": [{"name": "Dr. Anna Weber", "title": "Head of IT"}]},
        "demo": True,
        "meet_url": "https://meet.google.com/abc-defg-hij",
    })
    cid = call["call_id"]
    print("call:", cid, "| meet:", call["state"]["meet_url"])

    events = []
    async with websockets.connect(f"ws://localhost:8003/ws/events/{cid}") as ws:
        async def reader():
            try:
                async for msg in ws:
                    events.append(json.loads(msg))
            except websockets.ConnectionClosed:
                pass
        rt = asyncio.create_task(reader())

        # run the bot in demo (simulated join) mode with fast pacing
        proc = subprocess.Popen(
            [sys.executable, "-m", "bot.run", "--demo", "--call-id", cid, "--delay", "0.4"],
            cwd="/Users/ali/Desktop/Codes/minstra_hack/le-closer",
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        while proc.poll() is None:
            await asyncio.sleep(1)
        out = proc.stdout.read()
        rt.cancel()

    types = [e["type"] for e in events]
    bot_events = [e["payload"] for e in events if e["type"] == "bot.status"]
    print("bot statuses:", [(b["status"]) for b in bot_events])
    state = get(f"/calls/{cid}")
    print("segments:", len(state["segments"]))
    print("cards:", [(c["kind"], c["title"][:45]) for c in state["cards"]])
    print("tasks:", [(t["title"][:45], t["status"]) for t in state["tasks"]])
    print("numbers:", json.dumps(state["numbers"]))
    print("flow:", state["flow"]["stage"], state["flow"]["bant"])
    assert any(b["status"] == "in_call" for b in bot_events)
    assert any(b["status"] == "left" for b in bot_events)
    assert "transcript.segment" in types and "card.upsert" in types
    assert state["numbers"] and state["numbers"]["deal_value"] is not None
    print("BOT DEMO OK —", len(events), "events")


asyncio.run(main())
