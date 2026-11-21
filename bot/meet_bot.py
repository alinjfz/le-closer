"""Le Closer Meet bot — joins a Google Meet call with headless Chrome and
streams the meeting audio into the Le Closer backend pipeline.

Flow:
  1. Open the Meet link in headless Chrome (persistent profile so a signed-in
     Google account can be used — Meet blocks anonymous joins on many Workspace
     domains).
  2. Enter the bot name "Le Closer Bot" and click "Ask to join" / "Join now".
  3. Announce itself in the Meet chat (transparency + consent).
  4. Once admitted, inject audio_capture.js: incoming WebRTC audio tracks are captured
     directly, converted to PCM16/16kHz, and every chunk is pushed
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


# Installed before Meet creates peer connections, so capture uses remote audio
# directly and never waits for a screen-sharing picker in headless Chrome.
TRACK_PEERS_JS = """
(() => {
  window.__leCloserPeers = [];
  window.RTCPeerConnection = new Proxy(window.RTCPeerConnection, {
    construct(Target, args) {
      const peer = new Target(...args);
      window.__leCloserPeers.push(peer);
      return peer;
    }
  });
})();
"""


async def run_bot(meet_url: str, call_id: str, consent: bool = False, admit_timeout: int = 120) -> None:
    """Join a meeting only with explicit recording consent; always release Chrome."""
    if not consent:
        raise RuntimeError("Recording consent is required before the bot joins")
    import re
    from contextlib import suppress
    from playwright.async_api import async_playwright

    status = BotStatus(call_id)
    await status.post("launching", "starting Chrome")
    capture_js = (Path(__file__).parent / "audio_capture.js").read_text()
    async with async_playwright() as pw:
        profile = os.getenv("LECLOSER_CHROME_PROFILE", "/tmp/lecloser-chrome-profile")
        ctx = await pw.chromium.launch_persistent_context(
            profile, headless=True, args=CHROME_ARGS,
            viewport={"width": 1280, "height": 800}, locale="en-US",
        )
        writer = None
        try:
            await ctx.add_init_script(TRACK_PEERS_JS)
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            queue = asyncio.Queue(maxsize=400)

            def receive_pcm(chunk):
                if queue.full():
                    raise RuntimeError("Meeting audio upload cannot keep up")
                queue.put_nowait(chunk)

            await page.expose_function("__leCloserSendPCM", receive_pcm)
            await status.post("joining", meet_url)
            await page.goto(meet_url, wait_until="domcontentloaded", timeout=60000)
            # First-time Meet profiles can show this dialog before the prejoin
            # controls. The bot never needs to publish its mic or camera.
            without_devices = page.get_by_role(
                "button", name=re.compile("Continue without microphone and camera", re.I)
            ).first
            try:
                await without_devices.click(timeout=5000)
            except Exception:
                pass  # This onboarding prompt is not shown on every visit.
            text = await page.inner_text("body")
            if "you can't join this video call" in text.lower():
                raise RuntimeError(
                    "Google Meet rejected the bot's browser before admission. "
                    "The page does not explain the cause; this can still occur with Open meeting access. "
                    "The current bot uses a separate headless Chrome profile, and API OAuth does not sign "
                    "that browser in. Next steps: add interactive browser sign-in for the bot, or implement "
                    "meeting-tab audio capture in your own browser. Neither alternative is implemented yet."
                )
            try:
                await page.locator('input[aria-label*="name" i], input[placeholder*="name" i]').first.fill(BOT_NAME, timeout=8000)
            except Exception:
                pass

            # Keep the bot's virtual mic/camera off before admission.
            for label in ("Turn off microphone", "Turn off camera"):
                button = page.get_by_role("button", name=re.compile(label, re.I)).first
                if await button.is_visible():
                    await button.click()

            join = page.get_by_role("button", name=re.compile(r"^(Ask to join|Join now|Join)$", re.I)).first
            try:
                await join.click(timeout=20000)
            except Exception as exc:
                text = (await page.inner_text("body"))[:600]
                raise RuntimeError("Meet join control unavailable. API authorization does not sign the bot's Chrome into Google. " + text) from exc
            await status.post("requested", "Admit Le Closer Bot in Google Meet")
            try:
                await page.get_by_role("button", name=re.compile("Leave call", re.I)).first.wait_for(timeout=admit_timeout * 1000)
            except Exception as exc:
                raise RuntimeError("Bot was not admitted. Check the host's join requests or the meeting's guest restrictions.") from exc
            await status.post("in_call", "admitted; announcing transcription")
            # Do not capture if the announcement cannot be delivered.
            await page.get_by_role("button", name=re.compile(r"chat|Chat with everyone", re.I)).first.click(timeout=10000)
            message = page.locator('textarea[aria-label*="message" i], input[placeholder*="message" i], div[contenteditable="true"]').first
            await message.fill(ANNOUNCE, timeout=10000)
            await page.keyboard.press("Enter")
            await page.evaluate("window.__leCloserConsentGiven = true")

            async def ws_writer():
                async with websockets.connect(f"{WS_BASE}/ws/audio/{call_id}/client", proxy=None) as ws:
                    while True:
                        chunk = await queue.get()
                        await ws.send(base64.b64decode(chunk))

            writer = asyncio.create_task(ws_writer())
            result = await page.evaluate(capture_js)
            if result != "capturing":
                raise RuntimeError(f"Audio capture did not start: {result}")
            # A remote audio chunk, not just a successful script injection, proves capture.
            for _ in range(100):
                if writer.done():
                    await writer
                if await page.evaluate("window.__leCloserAudioChunks > 0"):
                    break
                await asyncio.sleep(0.2)
            else:
                raise RuntimeError("No remote audio received. Have another participant join and speak, then retry.")
            await status.post("capturing", "remote meeting audio streaming to transcription")
            async with httpx.AsyncClient() as client:
                while True:
                    if writer.done():
                        await writer
                        raise RuntimeError("Audio forwarding stopped")
                    response = await client.get(f"{BACKEND}/calls/{call_id}")
                    response.raise_for_status()
                    if response.json().get("ended"):
                        break
                    if not await page.get_by_role("button", name=re.compile("Leave call", re.I)).first.is_visible():
                        break
                    await asyncio.sleep(1)
            await status.post("left", "call ended")
        finally:
            if writer:
                writer.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await writer
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
