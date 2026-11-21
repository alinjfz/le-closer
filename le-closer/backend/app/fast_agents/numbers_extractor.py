"""Numbers extractor (F9, D7) — LLM extracts facts, Python calculates."""
import re

from ..calculator import update_numbers
from ..router import add_card, new_id
from ..models import Card


def _extract(state, text: str) -> None:
    f = state.facts
    t = text.lower()
    m = re.search(r"(\d[\d,]*)\s*(?:users?|seats?|employees|people)", t)
    if m:
        f.seats = int(m.group(1).replace(",", ""))
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", t)
    if m and ("discount" in t or "at least" in t or "need" in t):
        f.requested_discount_pct = float(m.group(1))
    m = re.search(r"(?:budget(?: of| is)?|budget)\D{0,10}[€$]?\s*(\d[\d,]*(?:\.\d+)?)\s*(k|thousand)?", t)
    if m:
        val = float(m.group(1).replace(",", ""))
        if m.group(2):
            val *= 1000
        f.budget = val
    m = re.search(r"(\d+)\s*(?:year|yr)s?\s*(?:contract|deal)", t) or re.search(r"(\d+)\s*-?\s*years?", t)
    if m:
        f.contract_years = int(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\s*(?:saved|per)", t)
    if m:
        f.hours_saved_per_user = float(m.group(1))
    m = re.search(r"[€$]\s*(\d+(?:\.\d+)?)\s*(?:per|/)\s*(?:hour|user)", t)
    if m:
        f.hourly_cost = float(m.group(1))


async def run(state, store, segment, label) -> None:
    _extract(state, segment.text)
    await update_numbers(state, store)
    n = state.numbers
    if n and n.deal_value:
        await add_card(state, store, Card(
            id=new_id("card"), kind="deal",
            title="Deal numbers updated",
            body=(f"Deal value ≈ {n.deal_value:,.0f} {state.facts.currency} · "
                  f"floor {n.discount_floor_pct:.0f}% · "
                  f"{'within' if n.within_guardrails else 'OUTSIDE'} guardrails"),
            confidence=0.9, segment_id=segment.id,
        ))
