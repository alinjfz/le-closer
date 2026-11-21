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
    await add_card(state, store, Card(
        id=new_id("card"), kind="objection",
        title="Objection",
        body=body or "Acknowledge, reframe, ask what would work instead.",
        confidence=label.get("confidence", 0.8), segment_id=segment.id,
    ))
