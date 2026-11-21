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
client in the appropriate language and tone for the supplied context. Structure: greeting with title+surname,
summary, answers, next steps, attachments. No hype, precise facts."""

CULTURAL_BRIEF_SYSTEM = """Offer a brief, respectful communication briefing using the supplied
client context. Ask about preferred language, formality and terminology. Mention possible differences as
possibilities, never traits of a person or assumptions from nationality. Max 6 bullet lines."""


async def run_post_call(state: CallState, store: CallStore) -> None:
    await store.log_activity(state, "PostCallWorkflow", "building notes…", "working")
    transcript = "\n".join(f"{s.speaker.upper()}: {s.text}" for s in state.segments[-80:])
    notes_md = await chat_text(
        config.HEAVY_MODEL, NOTES_SYSTEM,
        f"Personal notes: {state.personal_notes}\nLive notes: {state.notes}\nActions: {[t.model_dump() for t in state.tasks]}\nTranscript:\n{transcript}\n\nFacts: {state.facts.model_dump()}\nFlow: {state.flow.model_dump()}",
    )
    state.notes = {"markdown": notes_md or "# Post-call notes\n(No API key — mock notes.)", "ts": time.time()}
    await store.emit(state.call_id, "notes.ready", state.notes)

    await store.log_activity(state, "PostCallWorkflow", "drafting follow-up email…", "working")
    state.followup_draft = await chat_text(
        config.HEAVY_MODEL, FOLLOWUP_SYSTEM,
        f"Notes:\n{notes_md}\nClient: {state.client.company}, {state.client.country}",
    ) or (
        f"Subject: Follow-up — Mistral Studio for {state.client.company}\n\n"
        f"Dear Dr. Weber,\n\nThank you for the call today. As discussed, Mistral Studio …\n\n"
        "Best regards,\nThe Rep"
    )
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
