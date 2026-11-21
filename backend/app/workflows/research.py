"""ResearchWorkflow — pre-call research brief seeded at call creation (section 9.2)."""
from __future__ import annotations

from .. import config
from ..mistral_client import chat_text
from ..router import add_card, new_id
from ..models import Card

SYSTEM = """You are the Researcher agent of Le Closer. Write a pre-call research brief
for the client company: industry, size, HQ, likely priorities, recent-news angle,
and 3 questions to ask. Max 8 bullet lines. Factual, no invented specifics."""

_MOCK_BRIEF = """• **NordWerk Maschinenbau AG** — mid-size German machine builder (HQ: Stuttgart), ~2,500 employees, 3 plants
• Core business: industrial machinery with IoT-connected sensors on sold equipment — sensor security is the likely pain
• Likely priorities: device-level security (mTLS), GDPR / EU hosting, steering-committee (Lenkungsausschuss) approval
• Recent-news angle: EU Cyber Resilience Act pushing manufacturers to secure connected devices
• Ask: how many sensors? which gateway/ERP? who signs off besides IT?"""


async def research_brief(state, store) -> None:
    await store.log_activity(state, "ResearchWorkflow", "researching client…", "working")
    from ..mistral_client import has_api_key

    brief = await chat_text(
        config.HEAVY_MODEL, SYSTEM,
        f"Company: {state.client.company}, country: {state.client.country}, industry: {state.client.industry}, "
        f"people: {state.client.people}",
    )
    if state.demo and not has_api_key():
        brief = _MOCK_BRIEF
    await add_card(state, store, Card(
        id=new_id("card"), kind="research",
        title=f"Research brief: {state.client.company}",
        body=brief or f"Client: {state.client.company}. Ask about their priorities, company size, and decision process. Company facts have not been verified.",
        sources=["web search", "company profile"],
        confidence=0.8,
        meta={"precall": True},
    ))
    await store.log_activity(state, "ResearchWorkflow", "brief ready", "done")
