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

### 🐳 Docker (recommended — one image, everything included)

```bash
cd le-closer
cp .env.example .env         # add MISTRAL_API_KEY / GOOGLE_APPLICATION_CREDENTIALS (optional)
docker build -t le-closer .  # ~1GB; code changes rebuild in ~2s (deps are cached layers)
docker run -p 8003:8003 le-closer
# open http://localhost:8003 — dashboard + API + WS on one port

# scripted demo call straight into the dashboard:
docker run --rm le-closer python -m bot.run --demo --create-call
# then in the UI: "Resume latest call ↻"

# real meeting:
docker run --rm -e LECLOSER_BACKEND=http://host.docker.internal:8003 \
  le-closer python -m bot.run --meet-url https://meet.google.com/xxx-yyyy-zzz --create-call

# or with compose (app + demo bot):
docker compose --profile demo up --build
```

The image is multi-stage: `node:20-alpine` builds the frontend, `python:3.12-slim`
runs FastAPI which also serves the built SPA (no nginx), and includes the
Playwright chromium-headless-shell for the Meet bot. Heavy layers (apt libs,
pip, browser) are ordered before the code `COPY`, so rebuilds after code edits
are seconds.

### Manual (dev)

```bash
# Backend
cd backend
pip install -r ../requirements.txt
uvicorn app.main:app --port 8003

# Frontend (dev server with proxy to :8003)
cd frontend
npm install
npm run dev                  # http://localhost:5173
```

Open the UI → enter client (default: **Müller Logistik GmbH**, Dr. Anna Weber) → enable
**demo mode** → **Start demo call** → ▶ **Play demo script**.

No API key? Everything still runs end-to-end in mock mode (deterministic router,
canned integration verdicts, plain-Python deal maths) so the demo works offline.

## 🤖 The Meet bot (joins real Google Meet calls)

`bot/` is a standalone service that **actually joins the call** — no meeting-bot
API needed, it drives a real (headless) Chrome:

```bash
cd le-closer
pip install -r bot/requirements.txt && playwright install chromium

# 1. create a call in the dashboard (paste a Meet link, or "+ Create space" via Meet API v2)
# 2. send the bot into the meeting:
python -m bot.run --meet-url https://meet.google.com/xxx-yyyy-zzz --call-id <call_id>

# or let the bot create everything itself:
python -m bot.run --create-call --meet-url https://meet.google.com/xxx-yyyy-zzz

# offline / stage-safe simulated join (plays the realistic scripted call):
python -m bot.run --demo --call-id <call_id>
```

What the bot does: opens the Meet link in headless Chrome (persistent profile
`LECLOSER_CHROME_PROFILE` so a signed-in Google account works — Meet blocks
anonymous joins on many Workspace domains) → enters as **"Le Closer Bot"** →
clicks *Ask to join* → once admitted, **announces itself in the Meet chat** →
captures the meeting tab audio (`getDisplayMedia({audio:true})` → AudioWorklet
→ PCM16/16 kHz) → streams it to `ws://localhost:8003/ws/audio/{call_id}/client`,
i.e. straight into the same Voxtral/pipeline as everything else. Bot lifecycle
(`launching → joining → requested → in_call → capturing → left`) shows live in
the dashboard top bar.

**Consent-gated by design:** the setup screen requires the rep to confirm the
client's recording consent; the bot posts an announcement in the Meet chat
before capture starts; the demo script has the client explicitly agree. Google
Meet/Calendar integration for creating spaces uses `GOOGLE_APPLICATION_CREDENTIALS`
(Meet API v2 / Calendar API v3, see `bot/meet_api.py`).

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
├── bot/              Meet bot: Playwright joiner + consent-gated audio capture + Meet/Calendar API
│   ├── meet_bot.py       joins the call, streams PCM to the backend WS
│   ├── audio_capture.js  in-page PCM16 capture (consent-gated)
│   ├── meet_api.py       Meet API v2 spaces / Calendar conferenceData
│   └── run.py            CLI: --meet-url | --create-space | --demo
├── backend/          FastAPI app (models, state, router, fast_agents, workflows, audio_gateway)
│   ├── data/         pricing.yaml, faq, competitor notes
│   └── demo/         script.json (realistic scripted sales call)
└── frontend/         React + Vite + TS + Tailwind + Zustand + markmap
```

## Tests

```bash
cd backend
python3 test_api.py   # REST pipeline end-to-end
python3 test_ws.py    # WebSocket event stream end-to-end
```
