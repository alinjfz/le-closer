"""Le Closer — FastAPI backend. Endpoints per plan section 11.1."""
from __future__ import annotations

import asyncio
import json
import time

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .models import CallState
from .segments import make_segment, is_duplicate
from .state import store
from .router import route_segment, dispatch_labels
from .workflows import post_call
from .audio_gateway import VoxtralSession, get_sessions

app = FastAPI(title="Le Closer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/calls")
async def create_call(body: dict):
    state = store.create_call(
        client=body.get("client"),
        mode=body.get("mode", "sales"),
        demo=body.get("demo", False),
        meet_url=body.get("meet_url"),
    )
    # pre-call research + cultural briefing
    from .workflows import research
    asyncio.create_task(research.research_brief(state, store))
    asyncio.create_task(post_call.cultural_briefing(state, store))
    await store.log_activity(state, "LeCloser", f"call created ({state.client.company})", "done")
    return {"call_id": state.call_id, "state": state.model_dump()}


@app.post("/calls/{call_id}/meet")
async def attach_meet(call_id: str, body: dict):
    """Attach a Google Meet link to a call (bot will join it)."""
    state = store.get(call_id)
    if not state:
        return {"error": "not found"}
    state.meet_url = body.get("meet_url")
    await store.emit(call_id, "meet.update", {"meet_url": state.meet_url})
    return {"ok": True, "meet_url": state.meet_url}


@app.post("/calls/{call_id}/meet/create")
async def create_meet_space(call_id: str):
    """Create a fresh Google Meet space via Meet API v2 and attach it."""
    state = store.get(call_id)
    if not state:
        return {"error": "not found"}
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    try:
        from bot.meet_api import create_space
        space = create_space()
        state.meet_url = space.meeting_uri
        await store.emit(call_id, "meet.update", {"meet_url": space.meeting_uri,
                                                   "meeting_code": space.meeting_code})
        return {"ok": True, "meet_url": space.meeting_uri, "meeting_code": space.meeting_code}
    except Exception as e:
        return {"error": str(e)}


@app.post("/calls/{call_id}/bot/status")
async def bot_status(call_id: str, body: dict):
    """The Meet bot reports its lifecycle status here."""
    state = store.get(call_id)
    if not state:
        return {"error": "not found"}
    state.bot_status = body.get("status", state.bot_status)
    state.bot_detail = body.get("detail", "")
    await store.emit(call_id, "bot.status", {"status": state.bot_status, "detail": state.bot_detail})
    return {"ok": True}


@app.get("/calls/latest")
async def get_latest_call():
    """Most recently created call — lets the UI resume the bot's call."""
    if not store.calls:
        return {"error": "none"}
    state = max(store.calls.values(), key=lambda s: s.started_at)
    return state.model_dump()


@app.get("/calls/{call_id}")
async def get_call(call_id: str):
    state = store.get(call_id)
    if not state:
        return {"error": "not found"}
    return state.model_dump()


@app.post("/calls/{call_id}/end")
async def end_call(call_id: str):
    state = store.get(call_id)
    if not state:
        return {"error": "not found"}
    state.ended = True
    await store.emit(call_id, "call.ended", {})
    asyncio.create_task(post_call.run_post_call(state, store))
    return {"ok": True}


@app.post("/calls/{call_id}/inject")
async def inject(call_id: str, body: dict):
    """Text fallback (D12): inject a line as rep or client and run the pipeline."""
    state = store.get(call_id)
    if not state:
        return {"error": "not found"}
    speaker = body.get("speaker", "client")
    text = body.get("text", "").strip()
    if not text:
        return {"error": "empty text"}
    if is_duplicate(state, text):
        return {"ok": True, "duplicate": True}
    seg = make_segment(state, speaker, text)
    await store.emit(call_id, "transcript.segment", seg.model_dump())
    # dispatch agents in the background so the transcript is instant and cards stream in
    asyncio.create_task(_dispatch(state, seg))
    return {"ok": True, "segment_id": seg.id}


async def _dispatch(state: CallState, seg) -> None:
    try:
        result = await route_segment(state, store, seg)
        await dispatch_labels(state, store, seg, result.get("labels", []))
    except Exception as e:
        await store.log_activity(state, "pipeline", f"dispatch error: {e}", "error")


@app.post("/calls/{call_id}/demo/play")
async def demo_play(call_id: str, body: dict | None = None):
    """Stream the demo script lines through the pipeline (D12)."""
    from pathlib import Path

    state = store.get(call_id)
    if not state:
        return {"error": "not found"}
    script_path = Path(__file__).parent.parent / "demo" / "script.json"
    raw = json.loads(script_path.read_text()) if script_path.exists() else []
    lines = raw.get("lines", raw) if isinstance(raw, dict) else raw
    if not lines:
        lines = [
        {"speaker": "client", "text": "We run everything on SAP S/4HANA. Does your platform integrate with it?"},
        {"speaker": "rep", "text": "I'll send you the security document this week."},
        {"speaker": "client", "text": "We are about 300 users and would need at least 25% discount."},
    ]
    asyncio.create_task(_play_script(state, lines, body.get("delay", 2.0) if body else 2.0))
    return {"ok": True, "lines": len(lines)}


async def _play_script(state: CallState, lines: list[dict], delay: float) -> None:
    for line in lines:
        if state.ended:
            break
        await asyncio.sleep(delay)
        speaker = line.get("speaker", "client")
        text = line.get("text", "")
        if not text or is_duplicate(state, text):
            continue
        seg = make_segment(state, speaker, text)
        await store.emit(state.call_id, "transcript.segment", seg.model_dump())
        await _dispatch(state, seg)


@app.post("/calls/{call_id}/cards/{card_id}")
async def card_action(call_id: str, card_id: str, body: dict):
    state = store.get(call_id)
    if not state:
        return {"error": "not found"}
    action = body.get("action", "dismiss")
    for card in state.cards:
        if card.id == card_id:
            if action == "pin":
                card.status = "pinned"
            elif action == "dismiss":
                card.status = "dismissed"
            elif action == "useful":
                card.status = "pinned"
            await store.emit(call_id, "card.upsert", card.model_dump())
            return {"ok": True}
    return {"error": "card not found"}


@app.post("/calls/{call_id}/tasks/{task_id}")
async def task_action(call_id: str, task_id: str, body: dict):
    state = store.get(call_id)
    if not state:
        return {"error": "not found"}
    for task in state.tasks:
        if task.id == task_id:
            if "status" in body:
                task.status = body["status"]
            await store.emit(call_id, "task.upsert", task.model_dump())
            return {"ok": True}
    return {"error": "task not found"}


@app.post("/calls/{call_id}/prototype")
async def prototype(call_id: str, body: dict):
    """'Prototype this' button → PrototypeWorkflow (F10, D9)."""
    state = store.get(call_id)
    if not state:
        return {"error": "not found"}
    topic = body.get("topic", "the integration")
    html = (
        "<html><body style='font-family:sans-serif;background:#0f172a;color:#e2e8f0;"
        "padding:24px'><h2 style='color:#f59e0b'>Prototype: " + topic + "</h2>"
        "<p>This is a sandboxed mock-up of how the " + topic +
        " would look in Mistral Studio.</p>"
        "<button onclick=\"this.textContent='Synced ✓'\" style='padding:8px 16px;"
        "background:#f59e0b;border:none;border-radius:6px;cursor:pointer'>Run sync</button>"
        "</body></html>"
    )
    proto = {"id": f"proto_{int(time.time())}", "title": f"Prototype: {topic}", "html": html}
    state.prototypes.append(proto)
    await store.emit(call_id, "prototype.ready", proto)
    await store.log_activity(state, "PrototypeWorkflow", f"prototype ready: {topic}", "done")
    return {"ok": True, "prototype": proto}


@app.post("/calls/{call_id}/followup/decision")
async def followup_decision(call_id: str, body: dict):
    state = store.get(call_id)
    if not state:
        return {"error": "not found"}
    decision = body.get("decision", "approve")
    if decision == "approve":
        await post_call.approve_followup(state, store)
    else:
        await post_call.reject_followup(state, store)
    return {"ok": True, "status": state.followup_status}


@app.get("/calls/{call_id}/notes")
async def get_notes(call_id: str):
    state = store.get(call_id)
    if not state:
        return {"error": "not found"}
    return {"notes": state.notes, "followup_draft": state.followup_draft,
            "followup_status": state.followup_status}


@app.websocket("/ws/audio/{call_id}/{channel}")
async def ws_audio(websocket: WebSocket, call_id: str, channel: str):
    await websocket.accept()
    state = store.get(call_id)
    if not state:
        await websocket.close(code=4404)
        return
    session = get_sessions(call_id).get(channel)
    if session is None:
        session = VoxtralSession(state, store, channel)
        get_sessions(call_id)[channel] = session
    await session.connect()
    try:
        while True:
            data = await websocket.receive_bytes()
            await session.send_audio(data)
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/events/{call_id}")
async def ws_events(websocket: WebSocket, call_id: str):
    await websocket.accept()
    state = store.get(call_id)
    if not state:
        await websocket.close(code=4404)
        return
    queue = await store.bus.subscribe(call_id)
    try:
        # send full state first for (re)sync
        await websocket.send_json({"type": "state.sync", "payload": state.model_dump()})
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        await store.bus.unsubscribe(call_id, queue)
    except Exception:
        await store.bus.unsubscribe(call_id, queue)


@app.get("/health")
async def health():
    return {"ok": True, "calls": len(store.calls)}


# Serve the built frontend (Docker image) — mounted last so API/WS routes win.
_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="frontend")
