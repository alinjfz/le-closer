"""Thin wrapper around the Mistral SDK with a mock fallback when no API key is set.

The mock lets the whole pipeline run end-to-end without network access (demo mode,
CI). When MISTRAL_API_KEY is present, real models are used.
"""
from __future__ import annotations

import json
import re
from typing import Any

from . import config

_client = None


def has_api_key() -> bool:
    return bool(config.MISTRAL_API_KEY)


def get_client():
    global _client
    if _client is None and has_api_key():
        try:
            from mistralai import Mistral

            _client = Mistral(api_key=config.MISTRAL_API_KEY)
        except ImportError:
            # SDK not installed — fall back to mock mode
            return None
    return _client


def response_text(content: Any) -> str:
    """Only user-facing text; never stringify SDK thinking/tool chunks."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for chunk in content:
        kind = chunk.get("type") if isinstance(chunk, dict) else getattr(chunk, "type", None)
        text = chunk.get("text") if isinstance(chunk, dict) else getattr(chunk, "text", None)
        if kind == "text" and isinstance(text, str):
            parts.append(text)
    return "".join(parts)


async def chat_json(model: str, system: str, user: str, temperature: float = 0.2) -> dict[str, Any]:
    """Call chat completions and parse a JSON object out of the response."""
    client = get_client()
    if client is None:
        return _mock_router(user)
    import asyncio

    def _call():
        return client.chat.complete(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )

    resp = await asyncio.to_thread(_call)  # sync SDK must not block the event loop
    content = response_text(resp.choices[0].message.content) or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.DOTALL)
        return json.loads(m.group(0)) if m else {}


async def chat_text(model: str, system: str, user: str, temperature: float = 0.4) -> str:
    client = get_client()
    if client is None:
        return _mock_text(user)
    import asyncio

    def _call():
        return client.chat.complete(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )

    resp = await asyncio.to_thread(_call)
    return response_text(resp.choices[0].message.content)


# ---------------------------------------------------------------------------
# Mock fallback — deterministic keyword-based routing so the demo works offline
# ---------------------------------------------------------------------------

_INTEGRATION_RE = re.compile(
    r"\b(sap|s/4hana|salesforce|hubspot|workday|slack|teams|microsoft|oracle|netsuite|shopify)\b",
    re.IGNORECASE,
)
_OBJ_RE = re.compile(r"\b(too expensive|price|cost|budget concern|no budget|not now|maybe later|competitor is cheaper)\b", re.IGNORECASE)
_COMP_RE = re.compile(r"\b(competitor|alternative|instead of|other tools?|openai|anthropic|google|copilot)\b", re.IGNORECASE)
_PROMISE_RE = re.compile(r"\b(i'?ll send|i will send|i'll get you|i will get you|i'll share|i will share|send you the)\b", re.IGNORECASE)
_NUM_RE = re.compile(r"\b(\d[\d,]*)\s*(users?|seats?|employees|people)\b|\b(\d+(?:\.\d+)?)\s?%|\b(budget of|budget is)\s*€?\s?(\d[\d,]*)", re.IGNORECASE)
_CULTURAL_RE = re.compile(r"\b(gdpr|data protection|hosting|works council|betriebsrat|align internally|not possible|security)\b", re.IGNORECASE)
_QUESTION_RE = re.compile(r"\?\s*$|\b(do you|does it|can you|how does|what about|is it|are you)\b", re.IGNORECASE)


def _mock_router(user: str) -> dict[str, Any]:
    labels = []
    # Only classify the LATEST SEGMENT line, not the whole rolling context
    latest = user.rsplit("LATEST SEGMENT", 1)[-1]
    text = latest
    if _INTEGRATION_RE.search(text):
        m = _INTEGRATION_RE.search(text)
        labels.append({"type": "integration_question", "confidence": 0.93, "entity": m.group(1), "text": text[-160:]})
    if _OBJ_RE.search(text):
        labels.append({"type": "objection", "confidence": 0.85, "entity": "price", "text": text[-160:]})
    if _COMP_RE.search(text):
        labels.append({"type": "competitor_mention", "confidence": 0.8, "entity": _COMP_RE.search(text).group(1), "text": text[-160:]})
    if _PROMISE_RE.search(text):
        labels.append({"type": "promise", "confidence": 0.9, "entity": "follow-up item", "text": text[-160:]})
    m = _NUM_RE.search(text)
    if m:
        val = m.group(1) or m.group(3) or m.group(5)
        if val:
            labels.append({"type": "number_fact", "confidence": 0.88, "entity": "number", "value": val.replace(",", ""), "text": text[-160:]})
    if _CULTURAL_RE.search(text):
        labels.append({"type": "cultural_signal", "confidence": 0.82, "entity": _CULTURAL_RE.search(text).group(1), "text": text[-160:]})
    if _QUESTION_RE.search(text) and not labels:
        labels.append({"type": "product_question", "confidence": 0.75, "entity": "question", "text": text[-160:]})
    if not labels:
        labels.append({"type": "none", "confidence": 0.6, "entity": "", "text": text[-160:]})
    return {"labels": labels}


def _mock_text(user: str) -> str:
    return "Mock response (no MISTRAL_API_KEY set). The pipeline is running end-to-end."
