"""Competitor battlecard (F2)."""
from .. import config
from ..mistral_client import chat_text
from ..router import add_card, new_id
from ..models import Card

SYSTEM = """You are the Competitor agent of Le Closer. Write a context-specific battlecard
(not generic) for the competitor mentioned: 2 strengths to acknowledge, 2 differentiators
of Mistral Studio, 1 question to ask."""


async def run(state, store, segment, label) -> None:
    body = await chat_text(config.ROUTER_MODEL, SYSTEM, f"Competitor mentioned: {label.get('entity','?')}\nContext: {segment.text}")
    if not body:
        body = ("**Acknowledge:** their wrapper covers basic encryption — a fair baseline.\n"
                "**Differentiate:** we include per-device mTLS certificates, EU-only hosting (Paris) and a live integration check at **every** tier — no per-gateway fees.\n"
                "**Ask:** \"Does their quote include device certificates and EU residency?\"")
    await add_card(state, store, Card(
        id=new_id("card"), kind="competitor",
        title=f"Competitor: {label.get('entity','mentioned')}",
        body=body,
        confidence=label.get("confidence", 0.8), segment_id=segment.id,
    ))
