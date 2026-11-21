"""Rep-reference agent — when the rep references a quote / research result on the call
("send you the quote", "the whitepaper says..."), the corresponding card is dismissed
from the LIVE view (it stays in state for post-call notes). Demo beat: the copilot's
help is consumed in-call, before any follow-up is scheduled."""

from __future__ import annotations

import re

from ..router import new_id  # noqa: F401  (kept for symmetry with other agents)

# keyword in the rep's line -> card kinds to dismiss from the live view
_KIND_MAP = [
    (re.compile(r"\b(quote|pricing|tier)\b", re.IGNORECASE), {"deal"}),
    (re.compile(r"\b(sap|integration|connector)\b", re.IGNORECASE), {"integration"}),
    (re.compile(r"\b(whitepaper|pen-test|security doc|research|brief)\b", re.IGNORECASE), {"research"}),
]


async def run(state, store, segment, label) -> None:
    kinds: set[str] = set()
    for rx, ks in _KIND_MAP:
        if rx.search(segment.text):
            kinds |= ks
    if not kinds:
        return
    dismissed = []
    for card in state.cards:
        if card.kind in kinds and card.status in ("active", "pinned") and not card.meta.get("precall"):
            card.status = "dismissed"
            await store.emit(state.call_id, "card.upsert", card.model_dump())
            dismissed.append(card.title)
    if dismissed:
        await store.log_activity(
            state, "LiveCopilot",
            f"rep referenced it on the call -> removed from live view: {', '.join(dismissed[:3])} "
            "(kept for post-call notes)", "done",
        )
