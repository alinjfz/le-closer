"""Pydantic models for Le Closer — see plan section 10."""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class Segment(BaseModel):
    id: str
    speaker: Literal["rep", "client"]
    text: str
    start_ms: int
    end_ms: int
    translation: Optional[str] = None
    translation_language: Optional[str] = None
    source_language: Optional[str] = None
    cultural_note: Optional[str] = None


class Card(BaseModel):
    id: str
    kind: Literal[
        "answer", "integration", "objection", "competitor",
        "suggested_question", "cultural", "gap", "research",
        "negotiation", "deal", "prototype",
    ]
    title: str
    body: str
    sources: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    status: Literal["active", "pinned", "dismissed", "history"] = "active"
    segment_id: Optional[str] = None
    meta: dict = Field(default_factory=dict)


class Task(BaseModel):
    id: str
    title: str
    owner: Literal["rep", "agent", "client"]
    origin: Literal["promise", "open_question", "research", "integration", "prototype", "manual"]
    status: Literal["queued", "working", "ready", "done"]
    result_ref: Optional[str] = None


class FlowState(BaseModel):
    stage: Literal["rapport", "discovery", "demo", "objections", "pricing", "close"] = "rapport"
    bant: dict[str, Literal["unknown", "partial", "known"]] = Field(
        default_factory=lambda: {
            "budget": "unknown",
            "authority": "unknown",
            "need": "unknown",
            "timeline": "unknown",
        }
    )


class DealFacts(BaseModel):
    seats: Optional[int] = None
    sensors: Optional[int] = None
    plants: Optional[int] = None
    list_price_per_seat: Optional[float] = None
    currency: str = "EUR"
    requested_discount_pct: Optional[float] = None
    budget: Optional[float] = None
    contract_years: Optional[int] = None
    competitor_price_per_seat: Optional[float] = None
    hours_saved_per_user: Optional[float] = None
    hourly_cost: Optional[float] = None


class DealNumbers(BaseModel):
    deal_value: Optional[float] = None
    discount_floor_pct: float = 0.0
    price_at_requested_discount: Optional[float] = None
    margin_pct: Optional[float] = None
    client_roi_estimate: Optional[float] = None
    within_guardrails: bool = True
    # IoT scale quote (sensor volume tier)
    scale_tier: Optional[str] = None
    quote_per_sensor_month: Optional[float] = None
    quote_annual: Optional[float] = None
    quote_contract_total: Optional[float] = None


class ClientProfile(BaseModel):
    company: str = "NordWerk Maschinenbau AG"
    country: str = "DE"
    people: list[dict] = Field(default_factory=list)
    cultural_briefing: Optional[str] = None
    industry: str = "Manufacturing"


class ActivityEntry(BaseModel):
    agent: str
    message: str
    status: Literal["info", "working", "done", "error"] = "info"
    ts: float = 0.0


class AssistantSettings(BaseModel):
    tts_enabled: bool = True
    translation_language: str = Field(default="", max_length=80)


class CallState(BaseModel):
    call_id: str
    mode: Literal["sales", "brainstorm"] = "sales"
    demo: bool = False
    demo_status: Literal["idle", "playing", "finished"] = "idle"
    demo_progress: dict[str, int] = Field(default_factory=lambda: {"current": 0, "total": 0})
    client: ClientProfile = Field(default_factory=ClientProfile)
    segments: list[Segment] = Field(default_factory=list)
    cards: list[Card] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)
    flow: FlowState = Field(default_factory=FlowState)
    facts: DealFacts = Field(default_factory=DealFacts)
    numbers: Optional[DealNumbers] = None
    mindmap_md: str = "# Call\n## Waiting for conversation…"
    prototypes: list[dict] = Field(default_factory=list)
    activity: list[ActivityEntry] = Field(default_factory=list)
    notes: Optional[dict] = None
    followup_draft: Optional[str] = None
    followup_status: Literal["none", "awaiting_approval", "approved", "rejected", "sent"] = "none"
    ended: bool = False
    meet_url: Optional[str] = None
    bot_status: str = "offline"   # offline | launching | joining | requested | in_call | capturing | waiting | left
    bot_detail: str = ""
    started_at: float = 0.0
    settings: AssistantSettings = Field(default_factory=AssistantSettings)
    assistant_answers: list[dict] = Field(default_factory=list)
    personal_notes: str = ""
    rep_name: str = "You"         # display name for the rep channel
