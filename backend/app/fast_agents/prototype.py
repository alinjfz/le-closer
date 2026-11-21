"""Prototype agent — rep asks for a live workflow diagram of the client's architecture
(prototype_request label). Builds a self-contained sandboxed HTML/SVG card and emits
prototype.ready, same shape as the POST /calls/{id}/prototype endpoint (F10, D9)."""

from __future__ import annotations

import re

from ..router import new_id

_SYSTEMS_RE = re.compile(r"\b(sap|s/4hana|erp|mqtt|gateway|sensors?|devices?|scada|mes|cloud|bi)\b", re.IGNORECASE)


def _detect_systems(text: str) -> list[str]:
    seen: list[str] = []
    for m in _SYSTEMS_RE.finditer(text):
        name = m.group(1).upper()
        if name == "S/4HANA":
            name = "SAP S/4HANA"
        if name not in seen:
            seen.append(name)
    return seen or ["SENSORS", "GATEWAY", "ERP"]


def _workflow_html(topic: str, systems: list[str]) -> str:
    safe = topic.replace("<", "&lt;").replace(">", "&gt;")
    # chain: SENSORS -> MQTT -> GATEWAY -> WRAPPER -> detected systems
    chain = ["SENSORS", "MQTT", "GATEWAY", "SECURITY WRAPPER"] + [s for s in systems if s not in ("SENSORS", "MQTT", "GATEWAY")]
    n = len(chain)
    width = 760
    box_w = min(150, (width - 40) // n - 20)
    boxes = []
    for i, label in enumerate(chain):
        x = box_w / 2 + 12 + i * ((width - box_w - 24) / max(n - 1, 1))
        highlight = label == "SECURITY WRAPPER"
        fill = "#2563eb" if highlight else "#f1f5f9"
        text_c = "#ffffff" if highlight else "#172033"
        boxes.append(
            f"<rect x='{x - box_w/2:.0f}' y='70' width='{box_w}' height='44' rx='8' fill='{fill}' stroke='#cbd5e1'/>"
            f"<text x='{x:.0f}' y='96' text-anchor='middle' font-size='11' font-weight='600' fill='{text_c}'>{label}</text>"
        )
        if i < n - 1:
            x2 = box_w / 2 + 12 + (i + 1) * ((width - box_w - 24) / max(n - 1, 1))
            boxes.append(
                f"<line x1='{x + box_w/2:.0f}' y1='92' x2='{x2 - box_w/2:.0f}' y2='92' stroke='#64748b' stroke-width='2' marker-end='url(#arr)'/>"
            )
    svg = (
        f"<svg viewBox='0 0 {width} 160' width='100%' xmlns='http://www.w3.org/2000/svg'>"
        "<defs><marker id='arr' markerWidth='8' markerHeight='8' refX='6' refY='3' orient='auto'>"
        "<path d='M0,0 L6,3 L0,6 z' fill='#64748b'/></marker></defs>"
        + "".join(boxes) +
        "<text x='20' y='145' font-size='11' fill='#64748b'>mTLS on every device · TLS 1.3 in transit · AES-256 at rest · EU hosting (Paris)</text>"
        "</svg>"
    )
    return (
        "<html><head><style>body{font-family:ui-sans-serif,system-ui,sans-serif;background:#ffffff;"
        "color:#172033;margin:0;padding:20px} h2{color:#2563eb;font-size:18px;margin:0 0 4px} "
        ".sub{color:#64748b;font-size:12px;margin-bottom:16px}</style></head>"
        f"<body><h2>Live workflow: {safe}</h2>"
        "<div class='sub'>Generated live by Le Closer from the call — sandboxed iframe, no build step.</div>"
        f"{svg}</body></html>"
    )


async def run(state, store, segment, label) -> None:
    from ..live_assistant import generate_prototype
    from ..mistral_client import has_api_key
    from ..segments import rolling_context

    if state.demo:
        topic = "client architecture"
        title = f"Workflow diagram: {topic}"
        if not any(pr.get("title") == title for pr in state.prototypes):
            systems = _detect_systems(rolling_context(state, 10000))
            proto = {
                "id": new_id("proto"), "title": title, "kind": "code",
                "html": _workflow_html(topic, systems),
            }
            state.prototypes.append(proto)
            await store.emit(state.call_id, "prototype.ready", proto)
            await store.log_activity(state, "PrototypeAgent", "demo workflow diagram ready", "done")
        if not has_api_key():
            return  # The Mistral generation option remains available when a key is configured.

    topic = "Generated workflow diagram from the call"
    if any(pr.get("title") == topic for pr in state.prototypes):
        return
    if any(task.title == f"Prototype: {topic}" and task.status == "working" for task in state.tasks):
        return
    await generate_prototype(state, store, topic, "code")
