# Le Closer

> **"Other sales copilots *tell* you things. Le Closer *does* things — live, during the call, and after it."**

A live, multi-agent sales copilot built on Mistral. It listens to a sales call,
understands what is happening, and **acts while you are still talking**: it researches,
checks integrations, builds prototypes, writes everything down, tracks the flow of the
call, crunches the deal numbers, and handles the follow-up after the call.

## Built with

- **Voxtral Realtime** — two-channel transcription (rep mic + meeting tab), turn detection, context biasing
- **Mistral Large (Le Chonk)** — heavy lifting: integration checks, research, prototypes, notes, follow-ups
- **Mistral Small** — the fast router that reacts within seconds
- **Mistral Agents** — specialist agents with web search and a code sandbox
- **Mistral Workflows** — durable pipelines, incl. the post-call flow with human approval

## Quick start

```bash
# Backend
cd backend
pip install -e .
cp ../.env.example ../.env   # add MISTRAL_API_KEY (optional: mock mode works without)
uvicorn app.main:app --port 8003

# Frontend
cd frontend
npm install
npm run dev                  # http://localhost:5173
```

Open the UI → enter client (default: **Müller Logistik GmbH**, Dr. Anna Weber) → enable
**demo mode** → **Start call** → ▶ **Play demo script** (or inject lines manually).

No API key? Everything still runs end-to-end in mock mode (deterministic router,
canned integration verdicts, plain-Python deal maths) so the demo works offline.

## Architecture

```
Browser (React) ──WS PCM──▶ FastAPI ──▶ Voxtral Realtime (×2 channels)
                                │
                        final segments ──▶ Router (Mistral Small)
                                │              ├─▶ fast agents → cards / flow / BANT / to-dos / mind map / numbers
                                │              └─▶ Mistral Workflows (Le Chonk) → integration check, research, prototype
                                ▼
                          CallState + event bus ──WS──▶ React dashboard
```

- **Fast lane (~2s):** router classifies each finished segment; small agents update cards, stage, BANT, promises, mind map, numbers.
- **Slow lane (durable):** Mistral Workflows run integration checks, research, prototypes, and the post-call pipeline (`wait_for_input` approval → send → reminder).
- **Numbers:** the LLM only extracts facts into structured JSON; plain Python computes deal value, discount floor, margin, ROI (LLMs can't do arithmetic reliably).
- **Demo mode (D12):** pre-recorded script + text injection run through the exact same pipeline — the demo works even if live audio fails on stage.

## Key features

| Feature | Where |
|---|---|
| Live two-channel transcript | `FlowPanel` → Transcript |
| Live cards (integration, objection, competitor, cultural, suggested question) | `CardsPanel` |
| Integration check with verdict + sources + confidence | slow lane workflow |
| Conversation flow + BANT tracker | `StageTracker`, `BantChecklist` |
| To-do / promise tracker | `TodoList` |
| Live mind map (markmap) | `MindMap` |
| Live deal numbers + guardrails + negotiation hints | `NumbersPanel`, top bar |
| Prototype panel (sandboxed iframe) | `PrototypeFrame` |
| Post-call notes + follow-up approval workflow | `PostCall` page |
| Cultural cues (German client) | cultural cue cards + pre-call briefing |
| Agent activity log | bottom `ActivityBar` |

## Repo layout

```
le-closer/
├── backend/          FastAPI app (models, state, router, fast_agents, workflows, audio_gateway)
│   ├── data/         pricing.yaml, faq, competitor notes
│   └── demo/         script.json (text-injection demo lines)
└── frontend/         React + Vite + TS + Tailwind + Zustand + markmap
```

## Tests

```bash
cd backend
python3 test_api.py   # REST pipeline end-to-end
python3 test_ws.py    # WebSocket event stream end-to-end
```
