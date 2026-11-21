"""In-memory CallState store + async event bus (D8)."""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from .models import CallState, ActivityEntry


class EventBus:
    """Simple async pub/sub. Each call has its own queue set."""

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, call_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        async with self._lock:
            self._subscribers.setdefault(call_id, set()).add(q)
        return q

    async def unsubscribe(self, call_id: str, q: asyncio.Queue) -> None:
        async with self._lock:
            subs = self._subscribers.get(call_id)
            if subs:
                subs.discard(q)
                if not subs:
                    del self._subscribers[call_id]

    async def publish(self, call_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            subs = list(self._subscribers.get(call_id, set()))
        for q in subs:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # drop oldest, push newest
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except Exception:
                    pass


class CallStore:
    """Holds one CallState per call_id, plus the event bus."""

    def __init__(self) -> None:
        self.bus = EventBus()
        self.calls: dict[str, CallState] = {}
        self.assistant_locks: dict[str, asyncio.Lock] = {}
        self.jobs: dict[str, set[asyncio.Task]] = {}
        self.live_revisions: dict[str, int] = {}
        self.pending_invocations: dict[tuple[str, str], tuple[float, str]] = {}

    def spawn(self, call_id: str, coroutine) -> asyncio.Task:
        task = asyncio.create_task(coroutine)
        jobs = self.jobs.setdefault(call_id, set())
        jobs.add(task)
        def finished(job):
            jobs.discard(job)
            if not job.cancelled():
                job.exception()  # retrieve failures; pipeline handlers log actionable errors
        task.add_done_callback(finished)
        return task

    async def stop_jobs(self, call_id: str):
        jobs = list(self.jobs.pop(call_id, set()))
        for job in jobs:
            job.cancel()
        if jobs:
            await asyncio.gather(*jobs, return_exceptions=True)
        self.assistant_locks.pop(call_id, None)
        self.live_revisions.pop(call_id, None)
        for key in list(self.pending_invocations):
            if key[0] == call_id:
                self.pending_invocations.pop(key, None)

    def create_call(
        self,
        client: dict | None = None,
        mode: str = "sales",
        demo: bool = False,
        meet_url: str | None = None,
        rep_name: str = "You",
    ) -> CallState:
        call_id = f"call_{uuid.uuid4().hex[:12]}"
        from .models import ClientProfile

        profile = ClientProfile(**(client or {}))
        state = CallState(call_id=call_id, mode=mode, demo=demo, client=profile,
                          meet_url=meet_url, started_at=time.time(), rep_name=rep_name)
        self.calls[call_id] = state
        return state

    def get(self, call_id: str) -> CallState | None:
        return self.calls.get(call_id)

    async def emit(self, call_id: str, event_type: str, payload: Any) -> None:
        await self.bus.publish(call_id, {"type": event_type, "payload": payload})

    async def log_activity(self, state: CallState, agent: str, message: str, status: str = "info") -> None:
        entry = ActivityEntry(agent=agent, message=message, status=status, ts=time.time())  # type: ignore[arg-type]
        state.activity.append(entry)
        if len(state.activity) > 200:
            state.activity = state.activity[-200:]
        await self.emit(state.call_id, "activity.log", entry.model_dump())


store = CallStore()
