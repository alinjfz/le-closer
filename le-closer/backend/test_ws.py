"""Verify the WebSocket event stream end-to-end."""
import asyncio
import json
import urllib.request

import websockets

BASE = "http://localhost:8000"


def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req).read())


async def main():
    call = post("/calls", {"client": {"company": "Müller Logistik GmbH", "country": "DE"}, "demo": True})
    cid = call["call_id"]
    print("call:", cid)

    events = []
    async with websockets.connect(f"ws://localhost:8000/ws/events/{cid}") as ws:
        async def reader():
            try:
                async for msg in ws:
                    events.append(json.loads(msg))
            except websockets.ConnectionClosed:
                pass
        rt = asyncio.create_task(reader())
        await asyncio.sleep(0.5)
        post(f"/calls/{cid}/inject", {"speaker": "client",
             "text": "We run everything on SAP S/4HANA. Does your platform integrate with it?"})
        await asyncio.sleep(3)
        post(f"/calls/{cid}/inject", {"speaker": "client",
             "text": "We are about 300 users and would need at least 25% discount."})
        await asyncio.sleep(2)
        post(f"/calls/{cid}/prototype", {"topic": "SAP integration"})
        await asyncio.sleep(1)
        rt.cancel()

    types = [e["type"] for e in events]
    print("event types:", types)
    assert "state.sync" in types
    assert "transcript.segment" in types
    assert "card.upsert" in types
    assert "task.upsert" in types
    assert "numbers.update" in types
    assert "prototype.ready" in types
    assert "activity.log" in types
    kinds = [e["payload"]["kind"] for e in events if e["type"] == "card.upsert"]
    print("card kinds:", kinds)
    print("WS OK —", len(events), "events")


asyncio.run(main())
