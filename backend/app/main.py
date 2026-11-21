"""Le Closer — FastAPI backend. Endpoints per plan section 11.1."""
from __future__ import annotations

import asyncio
import json
import time
import sys
from contextlib import asynccontextmanager, suppress
from urllib.parse import urlparse

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Literal

from .models import AssistantSettings
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .models import CallState
from .segments import make_segment, is_duplicate
from .state import store
from .router import run_segment
from .workflows import post_call
from .audio_gateway import VoxtralSession, get_sessions

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
bot_tasks: dict[str, asyncio.Task] = {}


async def stop_bot(call_id: str):
    task = bot_tasks.get(call_id)
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


@asynccontextmanager
async def lifespan(app):
    try:
        yield
    finally:
        for call_id in list(bot_tasks):
            await stop_bot(call_id)
        for call_id in list(store.calls):
            for session in list(get_sessions(call_id).values()):
                await session.close()
        for call_id in list(store.jobs):
            await store.stop_jobs(call_id)


app = FastAPI(title="Le Closer", version="0.1.0", lifespan=lifespan)


async def managed_bot(state):
    try:
        from bot.meet_bot import run_bot
        await run_bot(state.meet_url, state.call_id, consent=True)
    except asyncio.CancelledError:
        state.bot_status, state.bot_detail = "left", "call stopped"
        await store.emit(state.call_id, "bot.status", {"status": "left", "detail": state.bot_detail})
        raise
    except Exception as exc:
        state.bot_status, state.bot_detail = "error", str(exc)[:1000]
        await store.emit(state.call_id, "bot.status", {"status": "error", "detail": state.bot_detail})
        await store.log_activity(state, "Meet bot", state.bot_detail, "error")
    finally:
        bot_tasks.pop(state.call_id, None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/calls")
async def create_call(body: dict):
    if body.get("start_bot"):
        if body.get("demo"):
            return {"error": "Disable demo mode to join a real meeting."}
        if body.get("recording_consent") is not True:
            return {"error": "Recording consent is required before joining."}
        url = urlparse(body.get("meet_url") or "")
        if url.scheme != "https" or url.hostname != "meet.google.com" or not url.path.strip("/"):
            return {"error": "Enter a Google Meet link before starting a live call."}
        from .mistral_client import has_api_key
        if not has_api_key():
            return {"error": "Set MISTRAL_API_KEY to enable live transcription."}
        if any(not task.done() for task in bot_tasks.values()):
            return {"error": "A Meet bot is already running. End that call first."}
    state = store.create_call(
        client=body.get("client"),
        mode=body.get("mode", "sales"),
        demo=body.get("demo", False),
        meet_url=body.get("meet_url"),
        rep_name=body.get("rep_name", "You"),
    )
    # pre-call research + cultural briefing
    from .workflows import research
    store.spawn(state.call_id, research.research_brief(state, store))
    store.spawn(state.call_id, post_call.cultural_briefing(state, store))
    await store.log_activity(state, "LeCloser", f"call created ({state.client.company})", "done")
    if body.get("start_bot"):
        state.bot_status = "launching"
        bot_tasks[state.call_id] = asyncio.create_task(managed_bot(state))
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
        space = await asyncio.to_thread(create_space)
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
    if state.ended:
        return {"ok": True}
    state.ended = True
    await stop_bot(call_id)
    for session in list(get_sessions(call_id).values()):
        await session.close()
    await store.stop_jobs(call_id)
    await store.emit(call_id, "call.ended", {})
    store.spawn(call_id, post_call.run_post_call(state, store))
    return {"ok": True}


@app.post("/calls/{call_id}/inject")
async def inject(call_id: str, body: dict):
    """Text fallback (D12): inject a line as rep or client and run the pipeline."""
    state = store.get(call_id)
    if not state:
        return {"error": "not found"}
    if state.ended:
        raise HTTPException(409, "Call has ended")
    speaker = body.get("speaker", "client")
    if speaker not in ("rep", "client"):
        raise HTTPException(422, "Invalid speaker")
    text = body.get("text", "").strip()
    if not text:
        return {"error": "empty text"}
    if is_duplicate(state, text):
        return {"ok": True, "duplicate": True}
    seg = make_segment(state, speaker, text)
    await store.emit(call_id, "transcript.segment", seg.model_dump())
    # dispatch agents in the background so the transcript is instant and cards stream in
    store.spawn(call_id, _dispatch(state, seg))
    return {"ok": True, "segment_id": seg.id}


async def _dispatch(state: CallState, seg) -> None:
    try:
        await run_segment(state, store, seg)
    except Exception as e:
        await store.log_activity(state, "pipeline", f"dispatch error: {e}", "error")


@app.post("/calls/{call_id}/demo/play")
async def demo_play(call_id: str, body: dict | None = None):
    """Stream the demo script lines through the pipeline (D12)."""
    from pathlib import Path

    state = store.get(call_id)
    if not state:
        return {"error": "not found"}
    if state.ended:
        raise HTTPException(409, "Call has ended")
    if state.demo_status == "playing":
        return {"ok": True, "status": "playing"}
    script_path = Path(__file__).parent.parent / "demo" / "script.json"
    try:
        raw = json.loads(script_path.read_text(encoding="utf-8"))
        lines = raw.get("lines", []) if isinstance(raw, dict) else raw
    except (OSError, ValueError):
        raise HTTPException(503, "The complete demo script could not be loaded. Please restore backend/demo/script.json.")
    if not isinstance(lines, list) or not lines or any(
        not isinstance(line, dict) or line.get("speaker") not in ("rep", "client")
        or not isinstance(line.get("text"), str) or not line["text"].strip() for line in lines
    ):
        raise HTTPException(503, "The demo script is empty or invalid.")
    state.demo_progress = {"current": 0, "total": len(lines)}
    await store.emit(call_id, "demo.progress", state.demo_progress)
    state.demo_status = "playing"
    await store.emit(call_id, "demo.status", "playing")
    store.spawn(call_id, _play_script(state, lines, body.get("delay", 0.8) if body else 0.8))
    return {"ok": True, "lines": len(lines)}


async def _play_script(state: CallState, lines: list[dict], delay: float) -> None:
    # Emit every scripted turn on schedule. A single managed consumer preserves
    # agent ordering without allowing slow provider calls to pause the transcript.
    queue: asyncio.Queue = asyncio.Queue()

    async def process_turns():
        while True:
            segment = await queue.get()
            if segment is None or state.ended:
                return
            await _dispatch(state, segment)

    worker = store.spawn(state.call_id, process_turns())
    try:
        state.demo_progress = {"current": 0, "total": len(lines)}
        for index, line in enumerate(lines, 1):
            if state.ended:
                break
            await asyncio.sleep(delay)
            if state.ended:
                break
            seg = make_segment(state, line["speaker"], line["text"])
            await store.emit(state.call_id, "transcript.segment", seg.model_dump())
            state.demo_progress = {"current": index, "total": len(lines)}
            await store.emit(state.call_id, "demo.progress", state.demo_progress)
            queue.put_nowait(seg)
        queue.put_nowait(None)
        await worker
    finally:
        if not worker.done():
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)
        state.demo_status = "finished"
        await store.emit(state.call_id, "demo.status", "finished")


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
                if body["status"] not in ("queued", "working", "ready", "done"):
                    raise HTTPException(422, "Invalid task status")
                task.status = body["status"]
            await store.emit(call_id, "task.upsert", task.model_dump())
            return {"ok": True}
    return {"error": "task not found"}


class PrototypeRequest(BaseModel):
    topic: str = Field(default="", max_length=2000)
    based_on_call: bool = False
    kind: Literal["code", "image", "diagram"] = "code"


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class PersonalNotesRequest(BaseModel):
    text: str = Field(max_length=20000)


def active_call(call_id):
    state = store.get(call_id)
    if not state:
        raise HTTPException(404, "Call not found")
    if state.ended:
        raise HTTPException(409, "Call has ended")
    return state


@app.post("/calls/{call_id}/prototype")
async def prototype(call_id: str, body: PrototypeRequest):
    from .live_assistant import generate_prototype
    state = active_call(call_id)
    if any(job.get_name() == "prototype-generation" and not job.done() for job in store.jobs.get(call_id, set())):
        raise HTTPException(409, "A prototype is already generating. Please wait for it to finish.")
    if body.kind == "diagram" and not state.demo:
        raise HTTPException(422, "The fixed workflow diagram is only available in demo mode.")
    topic = body.topic.strip()
    if body.based_on_call:
        if not state.segments and not state.notes and not state.personal_notes.strip():
            raise HTTPException(422, "Capture some conversation or add notes before generating from the call.")
        brief = "Visualize the end product discussed in our call" if body.kind == "image" else "Create a workflow diagram or prototype from our call"
        topic = brief + (f". Additional direction: {topic}" if topic else "")
    elif not topic:
        raise HTTPException(422, "Describe what you want to generate")
    job = store.spawn(call_id, generate_prototype(state, store, topic, body.kind))
    job.set_name("prototype-generation")
    return {"ok": True, "status": "working"}


@app.post("/calls/{call_id}/assistant/settings")
async def assistant_settings(call_id: str, body: AssistantSettings):
    state = active_call(call_id)
    from .mistral_client import has_api_key
    changes = body.model_dump(exclude_unset=True)
    if (changes.get("tts_enabled") or changes.get("translation_language")) and not has_api_key():
        raise HTTPException(422, "Set MISTRAL_API_KEY to enable translation and spoken answers.")
    previous_language = state.settings.translation_language
    state.settings = state.settings.model_copy(update=changes)
    await store.emit(call_id, "assistant.settings", state.settings.model_dump())
    # Apply a new target to the visible recent transcript too.
    if state.settings.translation_language and previous_language != state.settings.translation_language:
        from .live_assistant import translate_segment
        for segment in state.segments[-10:]:
            store.spawn(call_id, translate_segment(state, store, segment))
    return {"ok": True, "settings": state.settings.model_dump()}


@app.post("/calls/{call_id}/assistant/ask")
async def assistant_ask(call_id: str, body: QuestionRequest):
    from .live_assistant import answer_question
    state = active_call(call_id)
    async def answer():
        try:
            await answer_question(state, store, body.question)
        except Exception as exc:
            await store.log_activity(state, "Copilot", str(exc)[:300], "error")
    store.spawn(call_id, answer())
    return {"ok": True, "status": "working"}


@app.get("/calls/{call_id}/assistant/speech/{answer_id}")
async def assistant_speech(call_id: str, answer_id: str):
    from .mistral_media import generate_speech
    state = active_call(call_id)
    if not state.settings.tts_enabled:
        raise HTTPException(409, "Spoken answers are off")
    answer = next((a for a in state.assistant_answers if a['id'] == answer_id), None)
    if not answer:
        raise HTTPException(404, "Answer not found")
    try:
        audio = await generate_speech(answer['text'][:6000])
    except Exception:
        raise HTTPException(502, "Speech unavailable. Check Mistral TTS model and voice access.")
    return Response(audio, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})


@app.post("/calls/{call_id}/notes/personal")
async def personal_notes(call_id: str, body: PersonalNotesRequest):
    state = store.get(call_id)
    if not state:
        raise HTTPException(404, "Call not found")
    state.personal_notes = body.text
    await store.emit(call_id, "notes.personal", body.text)
    return {"ok": True}


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
    if channel not in ("rep", "client") or state.ended:
        await websocket.close(code=4400)
        return
    session = get_sessions(call_id).get(channel)
    if session is not None:
        await websocket.close(code=4409, reason="Audio channel is already connected")
        return
    session = VoxtralSession(state, store, channel)
    get_sessions(call_id)[channel] = session
    try:
        await session.connect()
        while True:
            data = await websocket.receive_bytes()
            await session.send_audio(data)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        await store.log_activity(state, "Transcription", str(exc)[:500], "error")
        await websocket.close(code=1011, reason="Transcription failed; see activity log")
    finally:
        await session.close()
        get_sessions(call_id).pop(channel, None)


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
