"""PostCallWorkflow — builds notes + follow-up, waits for rep approval (F11/F12).

With a real MISTRAL_API_KEY this would be a durable Mistral Workflow with
wait_for_input(); here it runs as an asyncio task against the same CallState
so the full approve → send → remind loop works in demo mode too.
"""
from __future__ import annotations

import asyncio
import time

from .. import config
from ..mistral_client import chat_text, has_api_key
from ..state import CallStore
from ..models import CallState

NOTES_SYSTEM = """You are the Notes writer of Le Closer. Given a sales call transcript and
state, produce post-call notes in Markdown with sections: Summary, Client needs and pains,
Decisions, Objections & handling, Integration answers, Deal snapshot, BANT status,
Action items, Open questions. Be concise and factual."""

FOLLOWUP_SYSTEM = """You are the Follow-up writer of Le Closer. Draft a follow-up email to the
client (German company, formal tone, English). Structure: greeting with title+surname,
summary, answers, next steps, attachments. No hype, precise facts."""

CULTURAL_BRIEF_SYSTEM = """You are the Cultural briefer of Le Closer. Write a pre-call cultural
briefing for a German B2B client (direct, factual, formal 'Sie', detail/data over hype,
GDPR & EU hosting, works council, consent to record). Max 10 bullet lines."""


_DEMO_NOTES = """# Post-call notes — {company}

## Summary
Discovery call with {person}. NordWerk runs ~1,200 IoT sensors across 3 plants, publishing MQTT to an on-prem gateway feeding SAP ERP via nightly batch. Interest in the security wrapper is driven by device-level security and GDPR / EU-hosting requirements.

## Client needs & pains
- Secure sensor traffic end-to-end (mTLS per device)
- GDPR compliance, EU-only hosting (Paris region)
- Reduce manual nightly-batch handling

## Decisions
- Must go through the **Lenkungsausschuss** (steering committee) before sign-off
- 2-year contract preferred

## Pricing / quote
- Volume tier: Plant (500–1,999 sensors) at €2.40/sensor/mo → **≈ €69,120/yr** (1,200 sensors, 2 yr)
- Scale-up: Enterprise tier (2,000+ sensors) drops to €1.80/sensor/mo

## Action items
- Quote, workflow diagram, whitepaper + pen-test summary were shared in the call chat during the call
- Kick off 2-week pilot next week after steering-committee approval
"""

_DEMO_FOLLOWUP = """Subject: Follow-up — IoT security wrapper for {company}

Dear Dr. Weber,

Thank you for the call today. As discussed:

- **Quote (shared in the call chat during our call):** Plant tier (500–1,999 sensors) — €2.40/sensor/month, ≈ €69,120/year for 1,200 sensors over 2 years. At 2,000+ sensors the Enterprise tier drops to €1.80/sensor/month.
- **Security:** mutual TLS on every device, TLS 1.3 in transit, AES-256 at rest, EU-only hosting (Paris), SOC 2 Type II — whitepaper and pen-test summary were shared in the call chat.
- **Architecture:** wrapper slots between your sensors and the on-prem gateway; SAP ERP integration via REST + MCP connector (workflow diagram shared in call chat).
- **Next steps:** 2-week pilot next week once the Lenkungsausschuss approves.

Best regards,
The Rep"""


async def run_post_call(state: CallState, store: CallStore) -> None:
    from ..mistral_client import has_api_key

    await store.log_activity(state, "PostCallWorkflow", "building notes…", "working")
    transcript = "\n".join(f"{s.speaker.upper()}: {s.text}" for s in state.segments[-80:])
    notes_md = await chat_text(
        config.HEAVY_MODEL, NOTES_SYSTEM,
        f"Transcript:\n{transcript}\n\nFacts: {state.facts.model_dump()}\nFlow: {state.flow.model_dump()}",
    )
    if not has_api_key():
        person = state.client.people[0]["name"] if state.client.people else "the client"
        notes_md = _DEMO_NOTES.format(company=state.client.company, person=person)
    state.notes = {"markdown": notes_md or "# Post-call notes\n(No API key — mock notes.)", "ts": time.time()}
    await store.emit(state.call_id, "notes.ready", state.notes)

    await store.log_activity(state, "PostCallWorkflow", "drafting follow-up email…", "working")
    state.followup_draft = await chat_text(
        config.HEAVY_MODEL, FOLLOWUP_SYSTEM,
        f"Notes:\n{notes_md}\nClient: {state.client.company}, {state.client.country}",
    )
    if not has_api_key():
        state.followup_draft = _DEMO_FOLLOWUP.format(company=state.client.company)
    state.followup_status = "awaiting_approval"
    await store.emit(state.call_id, "followup.awaiting_approval", state.followup_draft)
    await store.log_activity(state, "PostCallWorkflow", "waiting for rep approval (wait_for_input)", "working")


async def approve_followup(state: CallState, store: CallStore) -> None:
    if state.followup_status != "awaiting_approval":
        return
    state.followup_status = "approved"
    await store.log_activity(state, "PostCallWorkflow", "email approved → sending…", "working")
    await asyncio.sleep(1)
    state.followup_status = "sent"
    await store.emit(state.call_id, "followup.awaiting_approval", state.followup_draft)
    await store.log_activity(state, "PostCallWorkflow", "email sent · follow-up reminder scheduled (+3 days)", "done")


async def reject_followup(state: CallState, store: CallStore) -> None:
    state.followup_status = "rejected"
    await store.log_activity(state, "PostCallWorkflow", "email rejected by rep", "info")


async def cultural_briefing(state: CallState, store: CallStore) -> None:
    brief = await chat_text(
        config.HEAVY_MODEL, CULTURAL_BRIEF_SYSTEM,
        f"Client: {state.client.company}, country {state.client.country}, people: {state.client.people}",
    )
    state.client.cultural_briefing = brief or (
        "• Direct, factual communication — a clear 'no' is normal\n"
        "• Formal 'Sie' + titles ('Dr. Weber') until invited otherwise\n"
        "• Detail, data, documentation persuade more than hype\n"
        "• Expect GDPR / EU-hosting / security questions\n"
        "• Works council (Betriebsrat) may be involved in decisions\n"
        "• Always ask consent before recording"
    )
    await store.log_activity(state, "CulturalBriefer", "pre-call briefing ready", "done")
