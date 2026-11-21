"""Objection handler (F2)."""
from .. import config
from ..mistral_client import chat_text
from ..router import add_card, new_id
from ..models import Card

SYSTEM = """You are the Objection agent of Le Closer. For the objection below, give:
1) what the client really means, 2) a suggested reply, 3) a question to ask back.
Keep it under 4 lines."""


async def run(state, store, segment, label) -> None:
    body = await chat_text(
        config.ROUTER_MODEL, SYSTEM,
        f"Objection: {segment.text}",
    )
    if not body and state.demo:
        low = segment.text.lower()
        if "pric" in low or "cost" in low or "discount" in low:
            body = ("**What they mean:** budget pressure, not disinterest.\n"
                    "**Suggested reply:** at your scale (see quote card) you're already in a volume tier — the lever is contract length, not list price.\n"
                    "**Ask back:** \"Is the concern the total or the per-sensor rate?\"")
        elif "competitor" in low or "lower" in low:
            body = ("**What they mean:** a comparison is on the table.\n"
                    "**Suggested reply:** competitor quotes often exclude per-device security (mTLS) and EU hosting — both included in every tier here.\n"
                    "**Ask back:** \"What's included in their quote — device certs and EU residency?\"")
        else:
            body = "Acknowledge, reframe, ask what would work instead."
    if not body:
        body = "Acknowledge the concern and ask what evidence or terms would address it."
    await add_card(state, store, Card(
        id=new_id("card"), kind="objection",
        title="Objection",
        body=body,
        confidence=label.get("confidence", 0.8), segment_id=segment.id,
    ))
