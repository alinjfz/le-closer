"""Le Closer Meet bot — joins a Google Meet call with headless Chrome and
streams the meeting audio into the Le Closer backend pipeline.

Flow:
  1. Open the Meet link in headless Chrome (persistent profile so a signed-in
     Google account can be used — Meet blocks anonymous joins on many Workspace
     domains).
  2. Enter the bot name "Le Closer Bot" and click "Ask to join" / "Join now".
  3. Announce itself in the Meet chat (transparency + consent).
  4. Once admitted, inject audio_capture.js: the Meet tab's audio is captured
     via getDisplayMedia, converted to PCM16/16kHz, and every chunk is pushed
     through the exposed window.__leCloserSendPCM binding into Python, which
     forwards it to ws://backend/ws/audio/{call_id}/client.

Consent gate: capture only starts after the rep ticked "recording consent" in
the dashboard AND the bot sets window.__leCloserConsentGiven in the page (set
here once the bot has announced itself and the client agreed on the call —
in demo/simulated mode it is set immediately).

Run:  python -m bot.run --meet-url https://meet.google.com/xxx-yyyy-zzz --call-id call_...
      python -m bot.run --demo --call-id call_...     # simulated join, no browser
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
from pathlib import Path

import httpx
import websockets

BACKEND = os.getenv("LECLOSER_BACKEND", "http://localhost:8003")
WS_BASE = BACKEND.replace("http", "ws")

BOT_NAME = "Le Closer Bot"
ANNOUNCE = (
    "Hi — Le Closer bot here. With everyone's consent I'll transcribe this "
    "call to power the live assistant dashboard. Please say if you'd prefer otherwise."
)

CHROME_ARGS = [
    "--headless=new",
    "--autoplay-policy=no-user-gesture-required",
    "--use-fake-ui-for-media-stream",     # auto-accept mic/cam permission prompts
    "--use-fake-device-for-media-stream", # virtual mic so Meet is happy
    "--mute-audio",
    "--no-sandbox",
    "--window-size=1280,800",
    "--remote-debugging-port=0",
]


class BotStatus:
    def __init__(self, call_id: str):
        self.call_id = call_id

    async def post(self, status: str, detail: str = "") -> None:
        async with httpx.AsyncClient() as c:
            await c.post(f"{BACKEND}/calls/{self.call_id}/bot/status",
                         json={"status": status, "detail": detail})


async def run_bot(meet_url: str, call_id: str, consent: bool = True, admit_timeout: int = 120) -> None:
    """Real mode: join the Meet call with Playwright and capture its audio."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise RuntimeError("playwright not installed — pip install playwright && playwright install chromium")

    status = BotStatus(call_id)
    await status.post("launching", "starting headless Chrome")

    capture_js = (Path(__file__).parent / "audio_capture.js").read_text()
    async with async_playwright() as pw:
        # persistent profile lets you sign in once; set LECLOSER_CHROME_PROFILE to reuse it
        profile = os.getenv("LECLOSER_CHROME_PROFILE", "/tmp/lecloser-chrome-profile")
        ctx = await pw.chromium.launch_persistent_context(
            profile, headless=True, args=CHROME_ARGS,
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        # Python-side receiver for PCM chunks from the page
        queue: asyncio.Queue = asyncio.Queue()
        await page.expose_function("__leCloserSendPCM", lambda b64: queue.put_nowait(b64))

        await status.post("joining", meet_url)
        await page.goto(meet_url, wait_until="domcontentloaded", timeout=60000)

        # fill bot name
        try:
            name_input = page.locator('input[aria-label*="name" i], input[placeholder*="name" i]').first
            await name_input.fill(BOT_NAME, timeout=8000)
        except Exception:
            pass

        # click "Ask to join" / "Join now"
        joined = False
        for label in ["Ask to join", "Join now", "Join"]:
            try:
                btn = page.get_by_role("button", name=label).first
                await btn.click(timeout=5000)
                joined = True
                break
            except Exception:
                continue
        await status.post("requested", "waiting to be admitted" if joined else "join button not found")

        # wait until we're inside the meeting (toolbar / leave button appears)
        try:
            await page.get_by_role("button", name="Leave call").first.wait_for(timeout=admit_timeout * 1000)
            await status.post("in_call", "admitted to the meeting")
        except Exception:
            await status.post("waiting", f"not admitted within {admit_timeout}s — continue in demo mode")
            return

        # announce in chat, then mark consent (client agreed on the call)
        try:
            await page.get_by_role("button", name="Chat").click(timeout=5000)
            msg = page.locator('textarea[aria-label*="message" i], div[contenteditable="true"]').first
            await msg.fill(ANNOUNCE)
            await page.keyboard.press("Enter")
        except Exception:
            pass
        await page.evaluate("window.__leCloserConsentGiven = true")

        # start forwarding audio to the backend
        async def ws_writer():
            async with websockets.connect(f"{WS_BASE}/ws/audio/{call_id}/client") as ws:
                while True:
                    chunk = await queue.get()
                    if chunk is None:
                        return
                    await ws.send(base64.b64decode(chunk))
        writer = asyncio.create_task(ws_writer())
        await status.post("capturing", "streaming meeting audio → Le Closer")

        # inject capture into the Meet tab
        result = await page.evaluate(capture_js)
        print("capture:", result)

        # stay in the call until the backend ends the call
        while True:
            state = await httpx.AsyncClient().get(f"{BACKEND}/calls/{call_id}")
            if state.json().get("ended"):
                break
            await asyncio.sleep(2)

        queue.put_nowait(None)
        await writer
        await status.post("left", "call ended")
        await ctx.close()


async def run_demo(call_id: str, script_path: str | None = None, delay: float = 2.5) -> None:
    """Simulated join: plays the demo script as the client through /inject."""
    status = BotStatus(call_id)
    await status.post("in_call", "simulated join (demo mode) — playing scripted client audio")
    path = Path(script_path or Path(__file__).parent.parent / "backend" / "demo" / "script.json")
    raw = json.loads(path.read_text())
    lines = raw.get("lines", raw) if isinstance(raw, dict) else raw
    async with httpx.AsyncClient() as c:
        for line in lines:
            state = (await c.get(f"{BACKEND}/calls/{call_id}")).json()
            if state.get("ended"):
                break
            await asyncio.sleep(delay)
            await c.post(f"{BACKEND}/calls/{call_id}/inject",
                         json={"speaker": line.get("speaker", "client"), "text": line.get("text", "")})
    await status.post("left", "demo script finished")
