"""Knowledge base search over ingested docs (section 16.3).

Simple local keyword search over data/ docs; with an API key this would use
Mistral's managed search index. Fast agents use quick lookups here.
"""
from __future__ import annotations

from pathlib import Path

_DOCS_DIR = Path(__file__).parent.parent.parent / "data"
_cache: dict[str, str] = {}


def _load() -> dict[str, str]:
    if not _cache:
        for p in _DOCS_DIR.glob("*.md"):
            _cache[p.stem] = p.read_text(encoding="utf-8")
        docs = _DOCS_DIR / "docs"
        if docs.exists():
            for p in docs.rglob("*.md"):
                _cache[str(p.relative_to(docs))] = p.read_text(encoding="utf-8")
    return _cache


def search(query: str, top_k: int = 3) -> list[tuple[str, str]]:
    """Return [(source, snippet)] ranked by keyword overlap."""
    docs = _load()
    terms = query.lower().split()
    scored = []
    for name, text in docs.items():
        low = text.lower()
        score = sum(low.count(t) for t in terms)
        if score > 0:
            # first matching paragraph as snippet
            snippet = next((p.strip() for p in text.split("\n\n") if any(t in p.lower() for t in terms)), text[:200])
            scored.append((score, name, snippet))
    scored.sort(reverse=True)
    return [(n, s) for _, n, s in scored[:top_k]]
