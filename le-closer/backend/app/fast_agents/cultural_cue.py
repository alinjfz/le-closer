"""Cultural cue agent — German client persona (S1, section 14)."""
from .. import config
from ..mistral_client import chat_text
from ..router import add_card, new_id
from ..models import Card

SYSTEM = """You are the Cultural-cue agent of Le Closer. The client is German (Müller Logistik,
Dr. Anna Weber). Given a signal in the call, write a short cue card: what it may mean +
suggested adjustment. Frame as common tendencies, never facts about the person. 2 lines."""


async def run(state, store, segment, label) -> None:
    body = await chat_text(
        config.ROUTER_MODEL, SYSTEM,
        f"Signal: {segment.text}",
    )
    await add_card(state, store, Card(
        id=new_id("card"), kind="cultural",
        title="Cultural cue",
        body=body or "Detail-oriented questions signal serious interest — answer precisely.",
        confidence=label.get("confidence", 0.8), segment_id=segment.id,
    ))
