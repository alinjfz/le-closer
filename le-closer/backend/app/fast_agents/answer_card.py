"""Answer card agent — product questions (F2)."""
from .. import config
from ..mistral_client import chat_text
from ..router import add_card, new_id
from ..models import Card

SYSTEM = """You are the Answer agent of Le Closer. Answer the client's product question
in 2-4 sentences, based on Mistral Studio capabilities (agents, workflows, apps, Voxtral).
Be factual. End with a source hint like [Mistral docs]."""


async def run(state, store, segment, label) -> None:
    from ..knowledge.search import search

    hits = search(segment.text, top_k=2)
    kb_context = "\n".join(f"[{n}] {s}" for n, s in hits)
    answer = await chat_text(
        config.ROUTER_MODEL, SYSTEM,
        f"Question from {segment.speaker}: {segment.text}\nKnowledge base:\n{kb_context}",
    )
    sources = [n for n, _ in hits] or ["Mistral docs"]
    await add_card(state, store, Card(
        id=new_id("card"), kind="answer",
        title="Product answer",
        body=answer or "See Mistral Studio docs for details.",
        sources=sources, confidence=label.get("confidence", 0.8),
        segment_id=segment.id,
    ))
