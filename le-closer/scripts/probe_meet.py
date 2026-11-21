"""Probe what actually happens when the bot opens a Google Meet URL.

Run:  python scripts/probe_meet.py [meet_url]
Default URL: https://meet.google.com/new  (fresh meeting — needs sign-in)
        or pass an existing meeting link to see the anonymous "ask to join" flow.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://meet.google.com/new"


async def main():
    args = [
        "--headless=new",
        "--autoplay-policy=no-user-gesture-required",
        "--use-fake-ui-for-media-stream",
        "--use-fake-device-for-media-stream",
        "--mute-audio",
        "--no-sandbox",
    ]
    profile = os.getenv("LECLOSER_CHROME_PROFILE", "/tmp/lecloser-chrome-profile")
    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(profile, headless=True, args=args)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        print("opening", URL)
        try:
            await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print("GOTO FAILED:", str(e)[:200])
        await asyncio.sleep(6)
        print("title:", await page.title())
        print("url now:", page.url[:100])
        body = (await page.inner_text("body"))[:600].replace("\n", " | ")
        print("page text:", body)
        # look for the expected controls
        for label in ["Ask to join", "Join now", "Sign in", "name"]:
            try:
                el = page.get_by_role("button", name=label).first
                visible = await el.is_visible(timeout=1500)
                print(f"button '{label}': {'VISIBLE' if visible else 'hidden'}")
            except Exception:
                print(f"button '{label}': not found")
        try:
            inp = page.locator('input[aria-label*="name" i]').first
            print("name input:", "VISIBLE" if await inp.is_visible(timeout=1500) else "hidden")
        except Exception:
            print("name input: not found")
        await page.screenshot(path="/tmp/meet_probe.png")
        print("screenshot: /tmp/meet_probe.png")
        await ctx.close()


asyncio.run(main())
