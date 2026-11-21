"""Conversation flow tracker — stage + BANT (F5)."""

import re

from .. import config
from ..mistral_client import chat_json
from ..state import CallStore
from ..models import CallState

SYSTEM = """You track the sales call stage and BANT. Stages: rapport, discovery, demo,
objections, pricing, close. BANT keys: budget, authority, need, timeline; values: unknown,
partial, known. Return JSON: {"stage": ..., "bant": {...}} based on the conversation."""

STAGES = ["rapport", "discovery", "demo", "objections", "pricing", "close"]


_STAGE_HINTS = [
    (r"next steps|wrap up|let's wrap|ready to move|pilot", "close"),
    (r"competitor|too expensive|concern|objection|not sure|quoted lower", "objections"),
    (r"pric|quote|discount|budget|tier", "pricing"),
    (r"demo|show me|how does it work|prove it", "demo"),
    (r"architecture|sensors?|mqtt|gateway|process|current|need|pain|problem", "discovery"),
    (r"hello|thanks for|agenda|introduc", "rapport"),
]


def _mock_stage(state, segment) -> str:
    low = segment.text.lower()
    for rx, stage in _STAGE_HINTS:
        if re.search(rx, low):
            return stage
    return state.flow.stage


async def run(state: CallState, store: CallStore, segment, label: dict) -> None:
    from ..segments import rolling_context
    from ..mistral_client import has_api_key

    ctx = rolling_context(state, max_chars=2000)
    result = await chat_json(
        config.ROUTER_MODEL, SYSTEM,
        f"Conversation:\n{ctx}",
    )
    if not has_api_key():
        # deterministic demo progression through all stages + BANT from extracted facts
        bant = {}
        if state.facts.budget:
            bant["budget"] = "known"
        if state.facts.sensors:
            bant["need"] = "known"
        if state.facts.contract_years:
            bant["timeline"] = "partial"
        if any("lenkungsausschuss" in s.text.lower() for s in state.segments):
            bant["authority"] = "partial"
        result = {"stage": _mock_stage(state, segment), "bant": bant}
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
