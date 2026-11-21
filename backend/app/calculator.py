"""Deal maths + guardrails in plain Python (D7). LLM extracts facts, Python calculates."""
from __future__ import annotations

import yaml
from pathlib import Path

from . import config
from .models import CallState, DealFacts, DealNumbers

_PRICING: dict | None = None


def _load_pricing() -> dict:
    global _PRICING
    if _PRICING is None:
        path = Path(__file__).parent.parent / "data" / "pricing.yaml"
        if path.exists():
            _PRICING = yaml.safe_load(path.read_text()) or {}
        else:
            _PRICING = {}
    return _PRICING


def discount_floor_pct(seats: int | None, contract_years: int | None) -> float:
    """Floor depends on seats and contract length (section 15.2)."""
    pricing = _load_pricing()
    steps = pricing.get("discount_steps", [])
    floor = config.ABSOLUTE_DISCOUNT_FLOOR_PCT
    for step in steps:
        min_seats = step.get("min_seats", 0)
        min_years = step.get("min_years", 0)
        if (seats or 0) >= min_seats and (contract_years or 0) >= min_years:
            floor = max(floor, step.get("floor_pct", floor))
    return floor


def compute_numbers(facts: DealFacts) -> DealNumbers:
    pricing = _load_pricing()
    list_price = facts.list_price_per_seat or pricing.get("list_price_per_seat", config.DEFAULT_LIST_PRICE_PER_SEAT)
    cost = pricing.get("cost_per_seat", config.DEFAULT_COST_PER_SEAT)
    years = facts.contract_years or 1
    disc = facts.requested_discount_pct or 0.0

    deal_value = None
    price_at_disc = None
    margin = None
    if facts.seats:
        deal_value = facts.seats * list_price * 12 * years * (1 - disc / 100)
        price_at_disc = facts.seats * list_price * 12 * (1 - disc / 100)
        effective_price = list_price * (1 - disc / 100)
        if list_price > 0:
            margin = (effective_price - cost) / effective_price * 100

    floor = discount_floor_pct(facts.seats, facts.contract_years)
    within = (disc <= floor + 1e-9) if facts.requested_discount_pct is not None else True

    roi = None
    if facts.seats and facts.hours_saved_per_user:
        hourly = facts.hourly_cost or pricing.get("default_hourly_cost", 45.0)
        annual_value = facts.seats * facts.hours_saved_per_user * 12 * hourly
        price = facts.seats * list_price * 12
        if price > 0:
            roi = annual_value / price

    return DealNumbers(
        deal_value=deal_value,
        discount_floor_pct=floor,
        price_at_requested_discount=price_at_disc,
        margin_pct=margin,
        client_roi_estimate=roi,
        within_guardrails=within,
    )


async def update_numbers(state: CallState, store) -> None:
    state.numbers = compute_numbers(state.facts)
    await store.emit(state.call_id, "numbers.update", {
        "facts": state.facts.model_dump(),
        "numbers": state.numbers.model_dump(),
    })
