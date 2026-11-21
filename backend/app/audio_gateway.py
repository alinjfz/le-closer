"""Bridge mono PCM16/16 kHz audio to Voxtral's realtime WebSocket API."""
from __future__ import annotations

import asyncio
import base64
import json
import ssl
from contextlib import suppress
from urllib.parse import urlencode

from websockets.asyncio.client import connect
import certifi

from . import config
from .models import CallState
from .segments import make_segment, is_duplicate
from .state import CallStore


class VoxtralSession:
    def __init__(self, state: CallState, store: CallStore, channel: str):
        self.state, self.store, self.channel = state, store, channel
        self._closed = False
        self._partial = ""
        self._client = None
        self._reader = None
        self._flush_task = None
        self._dispatch_tasks = set()

    async def connect(self) -> None:
        if not config.MISTRAL_API_KEY:
            raise RuntimeError("MISTRAL_API_KEY is required for live transcription")
        url = "wss://api.mistral.ai/v1/audio/transcriptions/realtime?" + urlencode({"model": config.VOXTRAL_MODEL})
        self._client = await connect(url, additional_headers={"Authorization": f"Bearer {config.MISTRAL_API_KEY}"}, open_timeout=15, ssl=ssl.create_default_context(cafile=certifi.where()), proxy=None)
        event = json.loads(await asyncio.wait_for(self._client.recv(), 15))
        if event.get("type") != "session.created":
            raise RuntimeError(f"Voxtral session failed: {event}")
        await self._client.send(json.dumps({"type": "session.update", "session": {
            "audio_format": {"encoding": "pcm_s16le", "sample_rate": config.VOXTRAL_SAMPLE_RATE},
            "target_streaming_delay_ms": config.VOXTRAL_TARGET_DELAY_MS,
            "context_bias": config.CONTEXT_BIAS,
            "turn_detection": {},
        }}))
        event = json.loads(await asyncio.wait_for(self._client.recv(), 15))
        if event.get("type") != "session.updated":
            raise RuntimeError(f"Voxtral configuration failed: {event}")
        self._reader = asyncio.create_task(self._listen())

    async def _listen(self):
        async for message in self._client:
            event = json.loads(message)
            if event.get("type") == "error":
                raise RuntimeError(f"Voxtral: {event.get('error', event)}")
            await self.handle_event(event)
            if event.get("type") == "transcription.done":
                return

    async def send_audio(self, pcm: bytes) -> None:
        if self._reader and self._reader.done():
            await self._reader
            raise RuntimeError("Voxtral transcription session closed")
        await self._client.send(json.dumps({"type": "input_audio.append", "audio": base64.b64encode(pcm).decode()}))

    async def _flush_after_delay(self):
        await asyncio.sleep(config.VOXTRAL_TARGET_DELAY_MS / 1000 + 0.2)
        await self._finalize()

    async def _finalize(self):
        text, self._partial = self._partial.strip(), ""
        if not text or is_duplicate(self.state, text):
            return
        seg = make_segment(self.state, self.channel, text)
        await self.store.emit(self.state.call_id, "transcript.segment", seg.model_dump())

        if self.state.ended:
            return

        async def dispatch():
            try:
                from .router import run_segment
                await run_segment(self.state, self.store, seg)
            except Exception as exc:
                await self.store.log_activity(self.state, "Transcription router", str(exc)[:500], "error")

        task = self.store.spawn(self.state.call_id, dispatch())
        self._dispatch_tasks.add(task)
        task.add_done_callback(self._dispatch_tasks.discard)

    async def handle_event(self, event: dict) -> None:
        kind = event.get("type")
        if kind in ("transcription.text.delta", "transcript.delta"):
            text = event.get("text", "")
            self._partial += text
            await self.store.emit(self.state.call_id, "transcript.delta", {"speaker": self.channel, "text": text})
        elif kind == "turn.end":
            if self._flush_task:
                self._flush_task.cancel()
            self._flush_task = asyncio.create_task(self._flush_after_delay())
        elif kind in ("turn.start", "transcription.done"):
            if self._flush_task:
                self._flush_task.cancel()
            await self._finalize()

    async def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            if self._client and self._reader and not self._reader.done():
                await self._client.send(json.dumps({"type": "input_audio.end"}))
                with suppress(Exception):
                    await asyncio.wait_for(asyncio.shield(self._reader), 3)
        except Exception:
            pass
        finally:
            for task in (self._reader, self._flush_task):
                if task:
                    task.cancel()
                    with suppress(asyncio.CancelledError, Exception):
                        await task
            if self._client:
                await self._client.close()
            await self._finalize()
            for task in list(self._dispatch_tasks):
                task.cancel()
            if self._dispatch_tasks:
                await asyncio.gather(*self._dispatch_tasks, return_exceptions=True)


_sessions: dict[str, dict[str, VoxtralSession]] = {}


def get_sessions(call_id: str) -> dict[str, VoxtralSession]:
    return _sessions.setdefault(call_id, {})
