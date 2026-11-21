"""Integration question — fast lane creates a working to-do; the slow workflow
(IntegrationCheckWorkflow) produces the real researched answer (F3)."""
from ..router import add_card, add_task, new_id
from ..models import Card, Task

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
    await add_task(state, store, task)
    await store.log_activity(state, "IntegrationCheck", f"researching {entity}…", "working")

    # Simulate the slow workflow finishing shortly (real impl: Mistral Workflow)
    import asyncio
    await asyncio.sleep(1.5)
    task.status = "ready"
    await store.emit(state.call_id, "task.upsert", task.model_dump())
    await add_card(state, store, Card(
        id=new_id("card"), kind="integration",
        title=f"Integration: {entity}",
        body=f"**{verdict}.** {body}",
        sources=["Mistral docs", f"{entity} API docs"],
        confidence=0.86, segment_id=segment.id,
        meta={"entity": entity, "verdict": verdict, "prototype_available": verdict.startswith("via API")},
    ))
    task.result_ref = state.cards[-1].id
    await store.log_activity(state, "IntegrationCheck", f"{entity}: {verdict} (86%)", "done")
