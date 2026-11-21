"""Suggested next question (F4)."""
from .. import config
from ..mistral_client import chat_text
from ..router import add_card, new_id
from ..models import Card

SYSTEM = """You are the Suggested-Question agent of Le Closer. Given the current sales stage
and BANT status, suggest the single best next question to ask. One line."""


async def run(state, store, segment, label) -> None:
    bant = state.flow.bant
    q = await chat_text(
        config.ROUTER_MODEL, SYSTEM,
        f"Stage: {state.flow.stage}. BANT: {bant}. Latest: {segment.text}",
    )
    gaps = [k for k, v in bant.items() if v != "known"]
    title = "Ask next"
    if gaps:
        title = f"Ask next ({gaps[0]})"
    await add_card(state, store, Card(
        id=new_id("card"), kind="suggested_question",
        title=title, body=q or "Who else is involved in the decision?",
        confidence=0.85, segment_id=segment.id,
    ))
