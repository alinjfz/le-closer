"""Multilingual live cultural cues and the committed German demo persona."""
from .. import config
from ..mistral_client import chat_text
from ..router import add_card, new_id
from ..models import Card

LIVE_SYSTEM = """Explain a slang phrase, idiom or communication mismatch in the supplied utterance.
Explain possible meanings and a respectful clarification question. Use the speaker's words and context;
never infer personality or intentions from nationality. State uncertainty. Two concise lines."""

DEMO_SYSTEM = """You are the Cultural-cue agent of Le Closer. The client is German (NordWerk
Maschinenbau, Dr. Anna Weber). Given a signal in the call, write a short cue card: what it
may mean + suggested adjustment. Frame as common tendencies, never facts about the person.
2 lines."""

_PHRASES = {
    "lenkungsausschuss": (
        "'Lenkungsausschuss' = steering committee — a formal review board that must approve "
        "new vendor tooling. Expect a decision cycle there before sign-off: bring ROI, risk "
        "and security docs, not just a demo."
    ),
}


async def run(state, store, segment, label) -> None:
    low = segment.text.lower()
    known_phrase = next((phrase for phrase in _PHRASES if phrase in low), None)
    title = f'They said "{known_phrase}"' if known_phrase else "Cultural cue"
    if state.demo and known_phrase:
        body = _PHRASES[known_phrase]
    else:
        glossary = "Lenkungsausschuss means steering committee." if known_phrase else ""
        body = await chat_text(
            config.ROUTER_MODEL, DEMO_SYSTEM if state.demo else LIVE_SYSTEM,
            f"Client context: {state.client.country}. Signal: {segment.text}\nGlossary: {glossary}",
        )
        if not body:
            if state.demo and any(term in low for term in ("gdpr", "hosting", "eu")):
                body = ("Demo cue: clarify the EU hosting, security documentation and approval process "
                        "the client needs before proceeding.")
            else:
                body = glossary or "Ask the speaker to clarify the expression rather than assuming its meaning."
    await add_card(state, store, Card(
        id=new_id("card"), kind="cultural", title=title, body=body,
        confidence=label.get("confidence", 0.8), segment_id=segment.id,
    ))
