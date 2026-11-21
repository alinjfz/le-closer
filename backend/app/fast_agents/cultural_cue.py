"""Cultural cue agent — German client persona (S1, section 14)."""
from .. import config
from ..mistral_client import chat_text
from ..router import add_card, new_id
from ..models import Card

SYSTEM = """Explain a slang phrase, idiom or communication mismatch in the supplied utterance.
Explain possible meanings and a respectful clarification question. Use the speaker's words and context;
never infer personality or intentions from nationality. State uncertainty. Two concise lines."""


async def run(state, store, segment, label) -> None:
    body = await chat_text(
        config.ROUTER_MODEL, SYSTEM,
        f"Client context: {state.client.country}. Signal: {segment.text}",
    )
    await add_card(state, store, Card(
        id=new_id("card"), kind="cultural",
        title="Cultural cue",
        body=body or "Detail-oriented questions signal serious interest — answer precisely.",
        confidence=label.get("confidence", 0.8), segment_id=segment.id,
    ))
