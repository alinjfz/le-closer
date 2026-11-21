"""Prototype agent — rep asks for a live workflow diagram of the client's architecture
(prototype_request label). Builds a self-contained sandboxed HTML/SVG card and emits
prototype.ready, same shape as the POST /calls/{id}/prototype endpoint (F10, D9)."""

from __future__ import annotations

import re
import time

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
        x = 20 + i * ((width - 40) // max(n - 1, 1))
        highlight = label == "SECURITY WRAPPER"
        fill = "#f59e0b" if highlight else "#1e293b"
        text_c = "#0f172a" if highlight else "#e2e8f0"
        boxes.append(
            f"<rect x='{x - box_w/2:.0f}' y='70' width='{box_w}' height='44' rx='8' fill='{fill}' stroke='#334155'/>"
            f"<text x='{x:.0f}' y='96' text-anchor='middle' font-size='11' font-weight='600' fill='{text_c}'>{label}</text>"
        )
        if i < n - 1:
            x2 = 20 + (i + 1) * ((width - 40) // max(n - 1, 1))
            boxes.append(
                f"<line x1='{x + box_w/2:.0f}' y1='92' x2='{x2 - box_w/2:.0f}' y2='92' stroke='#64748b' stroke-width='2' marker-end='url(#arr)'/>"
            )
    svg = (
        f"<svg viewBox='0 0 {width} 160' width='100%' xmlns='http://www.w3.org/2000/svg'>"
        "<defs><marker id='arr' markerWidth='8' markerHeight='8' refX='6' refY='3' orient='auto'>"
        "<path d='M0,0 L6,3 L0,6 z' fill='#64748b'/></marker></defs>"
        + "".join(boxes) +
        "<text x='20' y='145' font-size='11' fill='#94a3b8'>mTLS on every device · TLS 1.3 in transit · AES-256 at rest · EU hosting (Paris)</text>"
        "</svg>"
    )
    return (
        "<html><head><style>body{font-family:ui-sans-serif,system-ui,sans-serif;background:#0f172a;"
        "color:#e2e8f0;margin:0;padding:20px} h2{color:#f59e0b;font-size:18px;margin:0 0 4px} "
        ".sub{color:#94a3b8;font-size:12px;margin-bottom:16px}</style></head>"
        f"<body><h2>Live workflow: {safe}</h2>"
        "<div class='sub'>Generated live by Le Closer from the call — sandboxed iframe, no build step.</div>"
        f"{svg}</body></html>"
    )


async def run(state, store, segment, label) -> None:
    topic = "client architecture"
    if any(pr.get("title") == f"Workflow diagram: {topic}" for pr in state.prototypes):
        return  # already produced during this call
    systems = _detect_systems(segment.text)
    proto = {
        "id": f"proto_{int(time.time())}",
        "title": f"Workflow diagram: {topic}",
        "html": _workflow_html(topic, systems),
    }
    state.prototypes.append(proto)
    await store.emit(state.call_id, "prototype.ready", proto)
    await store.log_activity(
        state, "PrototypeAgent",
        f"workflow diagram ready ({', '.join(systems[:4])})", "done",
    )
