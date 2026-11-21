"""Answer card agent — product questions (F2)."""

import re

from .. import config
from ..mistral_client import chat_text
from ..router import add_card, new_id
from ..models import Card

SYSTEM = """You are the Answer agent of Le Closer. Answer the client's product question
in 2-4 sentences, based on Mistral Studio capabilities (agents, workflows, apps, Voxtral).
Be factual. End with a source hint like [Mistral docs]."""


_DEMO_ANSWERS = [
    (r"mutual tls|mtls|tls|encrypt|certificate", "product",
     "Yes — every sensor wrapper enforces **mutual TLS (X.509 device certs)**; traffic is TLS 1.3 in transit and AES-256 at rest. Certificates are bulk-provisioned at onboarding, zero-touch. Latest independent pen-test summary is available under NDA."),
    (r"gdpr|data protection|hosting|eu", "product",
     "GDPR compliant with **EU-only data residency (Paris region)** — customer data never leaves the EU, and we never train on customer data. SOC 2 Type II report available on request."),
    (r"sap|erp|integrat", "product",
     "Yes — the platform connects to SAP ERP via its REST API + MCP connector, or pass-through at your gateway. Sync can be realtime or scheduled (e.g. nightly batch, like your current setup)."),
    (r"sensor|device|iot|mqtt|gateway", "product",
     "The wrapper sits between your sensors and the gateway: sensors publish MQTT to the wrapper, which terminates, inspects and re-encrypts the traffic before it reaches your gateway and ERP."),
]


async def run(state, store, segment, label) -> None:
    from ..knowledge.search import search
    from ..mistral_client import has_api_key

    hits = search(segment.text, top_k=2)
    kb_context = "\n".join(f"[{n}] {s}" for n, s in hits)
    answer = await chat_text(
        config.ROUTER_MODEL, SYSTEM,
        f"Question from {segment.speaker}: {segment.text}\nKnowledge base:\n{kb_context}",
    )
    if not answer and state.demo and not has_api_key():
        low = segment.text.lower()
        for rx, kind, text in _DEMO_ANSWERS:
            if re.search(rx, low):
                answer = text
                break
        answer = answer or "Based on the FAQ: we support anything with a REST API via MCP connectors, EU hosting, SOC 2 Type II."
    sources = [n for n, _ in hits] or ["faq.md"]
    await add_card(state, store, Card(
        id=new_id("card"), kind="answer",
        title="Product answer",
        body=answer or "See Mistral Studio docs for details.",
        sources=sources, confidence=label.get("confidence", 0.8),
        segment_id=segment.id,
    ))
