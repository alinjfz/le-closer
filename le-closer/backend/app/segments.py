"""Final-segment logic, de-duplication, rolling context (D6)."""
from __future__ import annotations

import time
import uuid

from . import config
from .models import CallState, Segment


def new_segment_id() -> str:
    return f"seg_{uuid.uuid4().hex[:8]}"


def make_segment(state: CallState, speaker: str, text: str, start_ms: int = 0, end_ms: int = 0) -> Segment:
    now_ms = int(time.time() * 1000)
    seg = Segment(
        id=new_segment_id(),
        speaker=speaker,  # type: ignore[arg-type]
        text=text.strip(),
        start_ms=start_ms or now_ms,
        end_ms=end_ms or now_ms,
    )
    state.segments.append(seg)
    return seg


def is_duplicate(state: CallState, text: str, window: int = 5) -> bool:
    """Skip if the same normalized text appeared in the last `window` segments."""
    norm = " ".join(text.lower().split())
    if len(norm) < 12:
        return False
    recent = state.segments[-window:]
    for s in recent:
        if " ".join(s.text.lower().split()) == norm:
            return True
    return False


def rolling_context(state: CallState, max_chars: int = config.ROLLING_CONTEXT_CHARS) -> str:
    """Last part of the conversation as 'REP: …\nCLIENT: …' lines."""
    lines = []
    total = 0
    for seg in reversed(state.segments):
        line = f"{seg.speaker.upper()}: {seg.text}"
        if total + len(line) > max_chars:
            break
        lines.append(line)
        total += len(line)
    return "\n".join(reversed(lines))
