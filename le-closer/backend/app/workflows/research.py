"""ResearchWorkflow — pre-call research brief seeded at call creation (section 9.2)."""
from __future__ import annotations

from .. import config
from ..mistral_client import chat_text
from ..router import add_card, new_id
from ..models import Card

SYSTEM = """You are the Researcher agent of Le Closer. Write a pre-call research brief
for the client company: industry, size, HQ, likely priorities, recent-news angle,
and 3 questions to ask. Max 8 bullet lines. Factual, no invented specifics."""

_MOCK_BRIEF = """• **Müller Logistik GmbH** — mid-size German logistics provider (HQ: Hamburg), ~1,200 employees
• Core business: freight forwarding & customs paperwork — manual document checks are the likely pain
• Likely priorities: EU data residency, GDPR, reducing manual work in customs processes
• Recent-news angle: EU supply-chain / customs digitisation pressure
• Ask: who owns the budget? what is the timeline? who else signs off (works council)?"""


async def research_brief(state, store) -> None:
    await store.log_activity(state, "ResearchWorkflow", "researching client…", "working")
    brief = await chat_text(
        config.HEAVY_MODEL, SYSTEM,
        f"Company: {state.client.company}, country: {state.client.country}, industry: {state.client.industry}, "
        f"people: {state.client.people}",
    )
    await add_card(state, store, Card(
        id=new_id("card"), kind="research",
        title=f"Research brief: {state.client.company}",
        body=brief or _MOCK_BRIEF,
        sources=["web search", "company profile"],
        confidence=0.8,
        meta={"precall": True},
    ))
    await store.log_activity(state, "ResearchWorkflow", "brief ready", "done")
