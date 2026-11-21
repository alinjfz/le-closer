"""Mind-map agent — maintains a Markdown outline, rendered by markmap (D10, F8)."""
from .. import config
from ..mistral_client import chat_text
from ..segments import rolling_context

SYSTEM = """You maintain a Markdown mind-map outline of a sales call.
Given the current outline and the latest conversation, return the UPDATED outline only.
Use '# Call' as root. Branches: Needs, Pains, People, Tools, Objections, Integrations,
Numbers, Next steps. Keep it concise (max 30 lines)."""


def _mock_mindmap(state, segment) -> str:
    """Deterministic demo outline: plots the client's architecture and where the
    sensors + security wrapper fit into it, updated as facts arrive."""
    f = state.facts
    sensors = f"{f.sensors:,} sensors" if f.sensors else "sensors"
    plants = f" across {f.plants} plants" if f.plants else ""
    lines = [
        "# Call",
        "## Current architecture",
        f"- {sensors}{plants} → MQTT → on-prem gateway → SAP ERP (nightly batch)",
        "- Security wrapper slots in between sensors and gateway (mTLS per device)",
        "## Needs & pains",
        "- Secure sensor traffic end-to-end (GDPR / EU hosting)",
        "- Reduce manual nightly-batch handling",
    ]
    if f.seats:
        lines += ["## People & scale", f"- ~{f.seats} operators"]
    if f.sensors:
        lines += ["## Pricing", f"- Volume tier quote for {f.sensors:,} sensors (see deal card)"]
    if any("lenkungsausschuss" in s.text.lower() for s in state.segments):
        lines += ["## Decision process", "- Lenkungsausschuss (steering committee) must approve"]
    lines += ["## Next steps", "- Quote, workflow diagram + whitepaper shared in call chat during the call → 2-week pilot next week"]
    return "\n".join(lines)


async def run(state, store, segment, label) -> None:
    from ..mistral_client import has_api_key

    ctx = rolling_context(state, max_chars=1500)
    updated = await chat_text(
        config.ROUTER_MODEL, SYSTEM,
        f"Current outline:\n{state.mindmap_md}\n\nLatest conversation:\n{ctx}",
    )
    if updated and updated.strip().startswith("#"):
        state.mindmap_md = updated.strip()
    elif state.demo and not has_api_key():
        state.mindmap_md = _mock_mindmap(state, segment)
    else:
        # fallback: append a line
        state.mindmap_md += f"\n- {segment.speaker}: {segment.text[:80]}"
    await store.emit(state.call_id, "mindmap.update", state.mindmap_md)
