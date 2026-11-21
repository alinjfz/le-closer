"""Router agent + label dispatch (fast lane, D5/D6)."""
from __future__ import annotations

import asyncio
import uuid

from . import config
from .mistral_client import chat_json, has_api_key
from .models import CallState, Card, Task
from .segments import rolling_context
from .state import CallStore

ROUTER_SYSTEM = """You are the Router agent of Le Closer, a live sales copilot.
Classify the latest sales-call segment into one or more labels.
Labels: product_question, integration_question, objection, competitor_mention,
buying_signal, risk_signal, promise, number_fact, decision_process,
cultural_signal, stage_hint, none.
Return JSON: {"labels": [{"type": ..., "confidence": 0-1, "entity": ..., "text": ...}]}
Only include labels with confidence >= 0.7."""


async def route_segment(state: CallState, store: CallStore, segment) -> dict:
    context = rolling_context(state)
    user_msg = f"CONVERSATION SO FAR:\n{context}\n\nLATEST SEGMENT ({segment.speaker}):\n{segment.text}"
    result = await chat_json(config.ROUTER_MODEL, ROUTER_SYSTEM, user_msg)
    labels = result.get("labels", [])
    await store.log_activity(state, "Router", f"classified segment → {[l['type'] for l in labels]}", "done")
    return result


async def dispatch_labels(state: CallState, store: CallStore, segment, labels: list[dict]) -> None:
    """Run the matching fast agent for each label. Import here to avoid cycles."""
    from .fast_agents import (
        answer_card, objection, competitor, suggested_question, flow_tracker,
        promise_tracker, numbers_extractor, mindmap, cultural_cue, integration_check,
    )

    handlers = {
        "product_question": answer_card.run,
        "objection": objection.run,
        "competitor_mention": competitor.run,
        "suggested_question": suggested_question.run,
        "promise": promise_tracker.run,
        "number_fact": numbers_extractor.run,
        "cultural_signal": cultural_cue.run,
        "integration_question": integration_check.run,
    }
    for label in labels:
        ltype = label.get("type", "none")
        if ltype in ("none", "stage_hint", "buying_signal", "risk_signal", "decision_process"):
            # flow tracker picks these up periodically; still log
            continue
        handler = handlers.get(ltype)
        if handler:
            try:
                await handler(state, store, segment, label)
            except Exception as e:
                await store.log_activity(state, f"agent:{ltype}", f"error: {e}", "error")

    # periodic flow + mindmap updates
    if len(state.segments) % 3 == 0:
        await flow_tracker.run(state, store, segment, {})
        await mindmap.run(state, store, segment, {})


def upsert_card(state: CallState, card: Card) -> Card:
    """Update existing card on same topic, else append. Enforce max active cards."""
    for existing in state.cards:
        if existing.kind == card.kind and existing.status in ("active", "pinned") and existing.title == card.title:
            existing.body = card.body
            existing.confidence = card.confidence
            existing.sources = card.sources
            return existing
    state.cards.append(card)
    # demote oldest active cards to history if over the limit
    active = [c for c in state.cards if c.status == "active"]
    while len(active) > config.MAX_ACTIVE_CARDS:
        oldest = active.pop(0)
        oldest.status = "history"
    return card


async def add_card(state: CallState, store: CallStore, card: Card) -> None:
    if card.confidence < config.CARD_CONFIDENCE_THRESHOLD:
        return
    card = upsert_card(state, card)
    await store.emit(state.call_id, "card.upsert", card.model_dump())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


async def add_task(state: CallState, store: CallStore, task: Task) -> None:
    state.tasks.append(task)
    await store.emit(state.call_id, "task.upsert", task.model_dump())
