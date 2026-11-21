"""Numbers extractor (F9, D7) — LLM extracts facts, Python calculates."""
import re

from ..calculator import update_numbers
from ..router import add_card, new_id
from ..models import Card


def _extract(state, text: str, speaker: str = "client") -> None:
    f = state.facts
    t = text.lower()
    m = re.search(r"(\d[\d,]*)\s*(?:users?|seats?|employees|people|operators?)", t)
    if m:
        f.seats = int(m.group(1).replace(",", ""))
    # scale facts (sensors/plants) only count when the CLIENT states them — a rep
    # mentioning a hypothetical ("if you scale past 2,000 sensors…") must not
    # overwrite the real architecture size.
    if speaker == "client":
        m = re.search(r"(\d[\d,]*)\s*(?:sensors?|devices?)", t)
        if m:
            f.sensors = int(m.group(1).replace(",", ""))
        m = re.search(r"(\d[\d,]*)\s*(?:plants?|sites?|factories)", t)
        if m:
            f.plants = int(m.group(1).replace(",", ""))
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", t)
    if m and ("discount" in t or "at least" in t or "need" in t):
        f.requested_discount_pct = float(m.group(1))
    m = re.search(r"budget\D{0,40}?[€$]?\s*(\d[\d,]*(?:\.\d+)?)\s*(k|thousand)?", t)
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
    _extract(state, segment.text, segment.speaker)
    await update_numbers(state, store)
    n = state.numbers
    if n and (n.deal_value or n.quote_annual):
        parts = []
        if n.quote_annual and state.facts.sensors:
            parts.append(
                f"Volume tier '{n.scale_tier}': €{n.quote_per_sensor_month:.2f}/sensor/mo "
                f"→ quote ≈ €{n.quote_annual:,.0f} {state.facts.currency}/yr "
                f"({state.facts.sensors:,} sensors); €{n.quote_contract_total:,.0f} total "
                f"over {state.facts.contract_years or 1} yr"
            )
            # scale-up suggestion: what the next tier up would cost at current volume
            from ..calculator import _load_pricing, tier_comparison
            tiers = tier_comparison(state.facts.sensors, state.facts.contract_years, _load_pricing())
            current_min = next((t["min_sensors"] for t in tiers if t["label"] == n.scale_tier), 0)
            nxt = next((t for t in tiers if t["min_sensors"] > current_min), None)
            if nxt:
                save = (n.quote_per_sensor_month - nxt["per_sensor_month"]) / n.quote_per_sensor_month * 100
                parts.append(
                    f"Scale-up: at {nxt['min_sensors']:,}+ sensors ('{nxt['label']}') the rate drops to "
                    f"€{nxt['per_sensor_month']:.2f}/sensor/mo → €{nxt['annual']:,.0f}/yr at your current volume "
                    f"({save:.0f}% cheaper per sensor)"
                )
        if n.deal_value and not n.quote_annual:
            parts.append(
                f"Deal value ≈ {n.deal_value:,.0f} {state.facts.currency} · "
                f"floor {n.discount_floor_pct:.0f}% · "
                f"{'within' if n.within_guardrails else 'OUTSIDE'} guardrails"
            )
        await add_card(state, store, Card(
            id=new_id("card"), kind="deal",
            title="Quote ready" if n.quote_annual else "Deal numbers updated",
            body="\n".join(parts),
            confidence=0.9, segment_id=segment.id,
        ))
