"""Ingest Mistral docs pages into data/docs/ (section 16.2).

Run manually: python -m app.knowledge.ingest
Without network access, ships the bundled faq.md / competitors.md only.
"""
from pathlib import Path

DOCS = Path(__file__).parent.parent.parent / "data" / "docs"

SOURCES = [
    "https://docs.mistral.ai/getting-started/quickstart",
    "https://docs.mistral.ai/capabilities/agents",
    "https://docs.mistral.ai/capabilities/workflows",
    "https://docs.mistral.ai/capabilities/voxtral",
    "https://docs.mistral.ai/security",
]


def ingest() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    try:
        import urllib.request
        for url in SOURCES:
            name = url.rstrip("/").split("/")[-1] + ".md"
            try:
                (DOCS / name).write_text(urllib.request.urlopen(url, timeout=10).read().decode()[:20000])
                print("ingested", name)
            except Exception as e:
                print("skip", url, e)
    except Exception as e:
        print("offline — using bundled docs only:", e)


if __name__ == "__main__":
    ingest()
