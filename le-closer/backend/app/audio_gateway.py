"""Audio gateway — receives PCM over WS, forwards to Voxtral Realtime (D2/D3/D4).

Without an API key, audio endpoints are inert; demo mode uses /inject instead.
Each call gets two Voxtral sessions (rep channel, client channel), turn detection on,
diarization off. Partial text → transcript.delta events; turn.end → final segment.
"""
from __future__ import annotations

import asyncio
import json

from . import config
from .mistral_client import has_api_key
from .models import CallState
from .segments import make_segment, is_duplicate
from .state import CallStore


class VoxtralSession:
    """One Voxtral Realtime session per channel."""

    def __init__(self, state: CallState, store: CallStore, channel: str):
        self.state = state
        self.store = store
        self.channel = channel  # "rep" | "client"
        self._partial = ""
        self._client = None

    async def connect(self) -> None:
        if not has_api_key():
            return
        # Real implementation would open mistralai realtime session here.
        # from mistralai import Mistral
        # self._client = Mistral(api_key=config.MISTRAL_API_KEY)

    async def send_audio(self, pcm: bytes) -> None:
        if self._client is None:
            return
        # Forward PCM to Voxtral; responses handled in _listen.

    async def handle_event(self, event: dict) -> None:
        etype = event.get("type", "")
        if etype == "transcript.delta":
            text = event.get("text", "")
            self._partial += text
            await self.store.emit(self.state.call_id, "transcript.delta", {
                "speaker": self.channel, "text": text,
            })
        elif etype == "turn.end":
            text = self._partial.strip()
            self._partial = ""
            if text and not is_duplicate(self.state, text):
                seg = make_segment(self.state, self.channel, text)
                await self.store.emit(self.state.call_id, "transcript.segment", seg.model_dump())
                import asyncio

                async def _dispatch():
                    from .router import route_segment, dispatch_labels
                    result = await route_segment(self.state, self.store, seg)
                    await dispatch_labels(self.state, self.store, seg, result.get("labels", []))

                asyncio.create_task(_dispatch())


_sessions: dict[str, dict[str, VoxtralSession]] = {}


def get_sessions(call_id: str) -> dict[str, VoxtralSession]:
    return _sessions.setdefault(call_id, {})
