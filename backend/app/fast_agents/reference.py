"""Track rep references without changing card visibility; dismissal is manual."""
from __future__ import annotations

import re

# Keyword in the rep's line -> card kinds to mark as referenced.
_KIND_MAP = [
    (re.compile(r"\b(quote|pricing|tier)\b", re.IGNORECASE), {"deal"}),
    (re.compile(r"\b(sap|integration|connector)\b", re.IGNORECASE), {"integration"}),
    (re.compile(r"\b(whitepaper|pen-test|security doc|research|brief)\b", re.IGNORECASE), {"research"}),
]


async def run(state, store, segment, label) -> None:
    if segment.speaker != "rep":
        return
    kinds = set()
    for rx, matches in _KIND_MAP:
        if rx.search(segment.text):
            kinds |= matches
    for card in state.cards:
        if card.kind in kinds and card.status in ("active", "pinned") and not card.meta.get("precall"):
            card.meta["referenced_on_call"] = True
            await store.emit(state.call_id, "card.upsert", card.model_dump())
    # Cards remain active/pinned until the user dismisses them.
