"""Mind-map agent — maintains a Markdown outline, rendered by markmap (D10, F8)."""
from .. import config
from ..mistral_client import chat_text
from ..segments import rolling_context

SYSTEM = """You maintain a Markdown mind-map outline of a sales call.
Given the current outline and the latest conversation, return the UPDATED outline only.
Use '# Call' as root. Branches: Needs, Pains, People, Tools, Objections, Integrations,
Numbers, Next steps. Keep it concise (max 30 lines)."""


async def run(state, store, segment, label) -> None:
    ctx = rolling_context(state, max_chars=1500)
    updated = await chat_text(
        config.ROUTER_MODEL, SYSTEM,
        f"Current outline:\n{state.mindmap_md}\n\nLatest conversation:\n{ctx}",
    )
    if updated and updated.strip().startswith("#"):
        state.mindmap_md = updated.strip()
    else:
        # fallback: append a line
        state.mindmap_md += f"\n- {segment.speaker}: {segment.text[:80]}"
    await store.emit(state.call_id, "mindmap.update", state.mindmap_md)
