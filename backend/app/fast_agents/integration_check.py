"""Integration question — fast lane creates a working to-do; the slow workflow
(IntegrationCheckWorkflow) produces the real researched answer (F3)."""
from ..router import add_card, add_task, new_id
from ..models import Card, Task
from .. import config
from ..mistral_client import chat_text, has_api_key

_MOCK_VERDICTS = {
    "sap": ("via API + MCP connector",
            "Mistral Studio connects to SAP S/4HANA via its REST/API layer and an MCP connector. "
            "OAuth2 auth, field mapping in Studio, sync every 15 min. Effort: medium."),
    "salesforce": ("native",
                   "Native Salesforce connector in Mistral Studio: bi-directional sync of accounts, "
                   "opportunities and custom objects. Effort: low."),
    "hubspot": ("native",
                "Native HubSpot connector: contacts, deals and tickets sync automatically. Effort: low."),
    "slack": ("native", "Native Slack app: agents can read and post in channels. Effort: low."),
}


async def run(state, store, segment, label) -> None:
    entity = (label.get("entity") or "the tool").strip()
    key = entity.lower().split()[0]
    verdict, body = _MOCK_VERDICTS.get(
        key, ("via API", f"Mistral Studio can integrate with {entity} via its public API and an MCP connector. Effort: medium.")
    )
    task = Task(
        id=new_id("task"), title=f"Check {entity} integration",
        owner="agent", origin="integration", status="working",
    )
    task = await add_task(state, store, task)
    await store.log_activity(state, "IntegrationCheck", f"researching {entity}…", "working")

    if has_api_key():
        from ..knowledge.search import search
        evidence = search(entity)
        body = await chat_text(config.HEAVY_MODEL,
            "You are an integration specialist. Use the supplied internal evidence to answer the question. "
            "Distinguish documented capabilities from proposed approaches. Do not invent native connectors, "
            "sources, or a completed web search. If evidence is insufficient, explain what must be verified. "
            "Return at most 100 words: a direct answer, the key uncertainty, and one useful follow-up question. "
            "Use short Markdown paragraphs or bullets.",
            f"Question: {segment.text}\nIntegration: {entity}\nInternal evidence: {evidence}")
        verdict = "Assessment — verify with technical owner"
    else:
        body = "Demo example (unverified): " + body
    task.status = "ready"
    await store.emit(state.call_id, "task.upsert", task.model_dump())
    card = await add_card(state, store, Card(
        id=new_id("card"), kind="integration",
        title=f"Integration: {entity}",
        body=f"**{verdict}.** {body}",
        sources=[],
        confidence=0.86, segment_id=segment.id,
        meta={"entity": entity, "verdict": verdict, "prototype_available": True},
    ))
    task.result_ref = card.id if card else None
    await store.emit(state.call_id, "task.upsert", task.model_dump())
    await store.log_activity(state, "IntegrationCheck", f"{entity}: {verdict} (86%)", "done")
