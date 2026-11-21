"""Conversation flow tracker — stage + BANT (F5)."""
from .. import config
from ..mistral_client import chat_json
from ..state import CallStore
from ..models import CallState

SYSTEM = """You track the sales call stage and BANT. Stages: rapport, discovery, demo,
objections, pricing, close. BANT keys: budget, authority, need, timeline; values: unknown,
partial, known. Return JSON: {"stage": ..., "bant": {...}} based on the conversation."""

STAGES = ["rapport", "discovery", "demo", "objections", "pricing", "close"]


async def run(state: CallState, store: CallStore, segment, label: dict) -> None:
    from ..segments import rolling_context

    ctx = rolling_context(state, max_chars=2000)
    result = await chat_json(
        config.ROUTER_MODEL, SYSTEM,
        f"Conversation:\n{ctx}",
    )
    stage = result.get("stage", state.flow.stage)
    if stage in STAGES and stage != state.flow.stage:
        state.flow.stage = stage  # type: ignore[assignment]
        await store.log_activity(state, "FlowTracker", f"stage → {stage}", "done")
    bant = result.get("bant", {})
    changed = False
    for k, v in bant.items():
        if k in state.flow.bant and v in ("unknown", "partial", "known") and v != state.flow.bant[k]:
            state.flow.bant[k] = v  # type: ignore[index]
            changed = True
    if changed:
        await store.log_activity(state, "FlowTracker", f"BANT → {state.flow.bant}", "done")
    await store.emit(state.call_id, "flow.update", state.flow.model_dump())
