"""Cultural cue agent — German client persona (S1, section 14)."""
from .. import config
from ..mistral_client import chat_text
from ..router import add_card, new_id
from ..models import Card

SYSTEM = """You are the Cultural-cue agent of Le Closer. The client is German (NordWerk
Maschinenbau, Dr. Anna Weber). Given a signal in the call, write a short cue card: what it
may mean + suggested adjustment. Frame as common tendencies, never facts about the person.
2 lines."""

# Deterministic decode for culturally specific phrases (used before the LLM fallback
# so the cue is correct in mock mode too).
_PHRASES = {
    "lenkungsausschuss": (
        "'Lenkungsausschuss' = steering committee — a formal review board that must approve "
        "new vendor tooling. Expect a decision cycle there before sign-off: bring ROI, risk "
        "and security docs, not just a demo."
    ),
}


async def run(state, store, segment, label) -> None:
    low = segment.text.lower()
    phrase_body = None
    phrase_title = None
    for phrase, meaning in _PHRASES.items():
        if phrase in low:
            phrase_body = meaning
            phrase_title = f'They said "{phrase}"'
            break
    if phrase_body:
        body, title = phrase_body, phrase_title
    else:
        body = await chat_text(
            config.ROUTER_MODEL, SYSTEM,
            f"Signal: {segment.text}",
        )
        title = "Cultural cue"
        if not body:
            low = segment.text.lower()
            if "gdpr" in low or "hosting" in low or "eu" in low:
                body = ("GDPR / EU-hosting questions are a buying signal, not an obstacle: German IT leads treat them as proof of seriousness. "
                        "Answer with specifics — Paris region, no training on customer data, SOC 2 Type II — and offer the DPA in writing.")
            else:
                body = "Detail-oriented questions signal serious interest — answer precisely."
    await add_card(state, store, Card(
        id=new_id("card"), kind="cultural",
        title=title,
        body=body,
        confidence=label.get("confidence", 0.8), segment_id=segment.id,
    ))
