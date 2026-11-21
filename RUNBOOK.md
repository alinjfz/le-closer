# Le Closer — Runbook: what to put where, and how to test it

Run the self-test any time:

```bash
python scripts/selftest.py        # all-in-one: backend, API pipeline, Mistral, Google, Playwright
python scripts/check_mistral.py   # Mistral key + chat call
python scripts/check_google.py    # Meet/Calendar API with your credentials
python scripts/probe_meet.py [meet_url]   # what the bot actually sees when opening a Meet link
python scripts/time_inject.py     # latency of one transcript line through the router
```

Current status on this machine (after fixes): **6/8 checks pass** — everything works
except the Google side, because no Google credentials/profile exist here yet.

---

## 1. `.env` — the only file you edit

```bash
cp .env.example .env
```

| Key | Required for | How to get it |
|---|---|---|
| `MISTRAL_API_KEY` | real LLM router/agents (without it the whole app silently runs in mock mode) | https://console.mistral.ai → API keys |
| `ROUTER_MODEL` | fast lane | default `mistral-small-latest` |
| `HEAVY_MODEL` | Le Chonk: research, integration, notes, follow-up | default `mistral-large-latest` |
| `VOXTRAL_MODEL` | realtime transcription | default `voxtral-mini-transcribe-realtime-latest` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Meet API v2 (`+ Create space` button, `bot --create-space`) | path to a Google Cloud key JSON — **see §3** |
| `LECLOSER_CHROME_PROFILE` | signed-in Chrome profile so the bot can join Meet | default `/tmp/lecloser-chrome-profile` — **see §4** |
| `LECLOSER_BACKEND` | where the bot sends audio | default `http://localhost:8003`; in docker-compose the bot uses `http://app:8003` |

**Dependency gotcha:** `requirements.txt` pins `mistralai>=1.0,<2`. Version 3.x
restructured the SDK (`from mistralai import Mistral` breaks). Always install
from `requirements.txt`, not bare `pip install mistralai`.

## 2. Start it

```bash
# Docker (recommended — one image, dashboard on :8003)
docker build -t le-closer . && docker run -p 8003:8003 --env-file .env le-closer
#   open http://localhost:8003

# or manually
cd backend && pip install -r ../requirements.txt && uvicorn app.main:app --port 8003
cd frontend && npm install && npm run dev   # dev UI on :5173, proxies to :8003
```

## 3. Google Cloud — Meet/Calendar API (for "+ Create space")

1. https://console.cloud.google.com → new project (or existing).
2. **Enable APIs**: *Google Meet API* (`meet.googleapis.com`) and *Google Calendar API*.
3. **OAuth consent screen** → External → add your Google account as a **test user**.
4. **Credentials → Create Credentials → OAuth client ID → Desktop app** → download JSON.
   (Service accounts also work for Calendar `conferenceData` with domain-wide
   delegation; for personal Gmail accounts use the OAuth Desktop client.)
5. `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/client_secret.json` — or put it
   in `.env` (the app loads `.env` via python-dotenv; export works too since
   `os.getenv` is checked).
6. Test: `python scripts/check_google.py` → should print `PASS Meet API v2 spaces.create → https://meet.google.com/...`
7. In the UI: **+ Create space** → a real Meet link appears and is attached to the call.

## 4. Signed-in Chrome profile (REQUIRED for the bot to join Meet)

Anonymous Chrome gets bounced to `accounts.google.com` sign-in (verified with
`scripts/probe_meet.py` — page title becomes "Sign in - Google Accounts").
On Google Workspace domains that don't allow anonymous joins, this is a hard wall.

One-time setup — sign in as the bot's Google account:

```bash
# headed Chrome via Playwright, sign into Google, then quit — the profile persists:
python - <<'EOF'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context("/tmp/lecloser-chrome-profile", headless=False)
    ctx.pages[0].goto("https://accounts.google.com")
    input("Sign in, then press Enter here...")
    ctx.close()
EOF
```

Then always run the bot with `LECLOSER_CHROME_PROFILE=/tmp/lecloser-chrome-profile`
(default). Verify: `python scripts/selftest.py` → "chrome profile signed into Google" PASS.

If the Workspace admin blocks third-party/less-secure access, add the Meet bot
account to the allowlist, or use an account with 2FA app-passwords disabled for bots
(recommended: a dedicated `lecloser-bot@yourdomain.com` account, added as a test
user / with AppSheet… no — just invite it to the Calendar event).

## 5. Run the bot into a real meeting

```bash
# 1. create the call in the UI (paste the Meet link) or:
CID=$(curl -s -X POST localhost:8003/calls -H 'Content-Type: application/json' \
  -d '{"demo":false,"meet_url":"https://meet.google.com/xxx-yyyy-zzz","client":{"company":"Müller Logistik GmbH","country":"DE"}}' | python3 -c "import sys,json;print(json.load(sys.stdin)['call_id'])")

# 2. send the bot in (same machine / docker host):
python -m bot.run --meet-url https://meet.google.com/xxx-yyyy-zzz --call-id $CID

# 3. watch the top bar: launching → joining → requested → in_call → capturing
#    admit the bot in Meet when it asks; it posts an announcement in the chat.
```

In Docker, from the host: `docker run --rm --env-file .env -e LECLOSER_BACKEND=http://host.docker.internal:8003 le-closer python -m bot.run --meet-url ... --call-id $CID`
(mount the chrome profile: `-v /tmp/lecloser-chrome-profile:/tmp/lecloser-chrome-profile`).

## 6. Test checklist (in order)

| # | Test | Command / action | Expected |
|---|---|---|---|
| 1 | deps | `pip install -r requirements.txt && playwright install chromium-headless-shell` | no errors |
| 2 | self-test | `python scripts/selftest.py` | 8/8 PASS (6/8 before Google setup) |
| 3 | Mistral key | `python scripts/check_mistral.py` | `PASS models.list`, `PASS chat.complete` |
| 4 | backend | `curl localhost:8003/health` | `{"ok":true,...}` |
| 5 | text pipeline | `python scripts/time_inject.py` | inject returns in <2s, cards stream in |
| 6 | dashboard | open http://localhost:8003 → Start demo call → ▶ Play demo script | transcript, cards, to-dos, numbers, mind map, activity bar all update live |
| 7 | Meet API | `python scripts/check_google.py` | `PASS spaces.create → meet link` |
| 8 | Meet page probe | `python scripts/probe_meet.py https://meet.google.com/xxx-yyyy-zzz` | buttons "Ask to join"/"Join now" visible (NOT the sign-in page) |
| 9 | bot joins | `python -m bot.run --meet-url ... --call-id ...` | top bar reaches `bot capturing audio`; transcript shows client speech |
| 10 | end call | End call button | notes + follow-up draft; **Approve & send** → status `sent` |
| 11 | docker | `docker build -t le-closer . && docker run -p 8003:8003 le-closer` | dashboard 200, `docker exec … python -m bot.run --demo --create-call` works |

## 7. Known limits (honest)

- **Voxtral Realtime audio forwarding is stubbed** in `audio_gateway.py` — PCM arrives
  over `/ws/audio/...` but the SDK realtime session is not wired yet; transcription of
  live audio currently flows through `/inject` (demo) — text pipeline is fully live.
- Meet selectors (button labels) change when Google updates the UI; the bot tries
  "Ask to join" / "Join now" / "Join" and waits for the "Leave call" button.
- Workspace domains can block bot accounts entirely (admin policy) — use a domain
  that allows it, or demo mode.
- The mock fallback (no `MISTRAL_API_KEY`) is deterministic and great for rehearsing
  the demo; with the key set, all agents use real Mistral models.
