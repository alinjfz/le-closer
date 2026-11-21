"""Le Closer self-test: checks every external dependency and endpoint, prints PASS/FAIL.

Run:  python scripts/selftest.py
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

BACKEND = os.getenv("LECLOSER_BACKEND", "http://localhost:8003")
results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def get(path):
    return json.loads(urllib.request.urlopen(BACKEND + path, timeout=5).read())


def post(path, body):
    req = urllib.request.Request(BACKEND + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=15).read())


# 1. backend
try:
    h = get("/health")
    check("backend /health", h.get("ok") is True, BACKEND)
except Exception as e:
    check("backend /health", False, str(e))

# 2. API pipeline (create call + inject + read state)
try:
    call = post("/calls", {"client": {"company": "SelfTest GmbH", "country": "DE"}, "demo": True})
    cid = call["call_id"]
    post(f"/calls/{cid}/inject", {"speaker": "client",
         "text": "We run SAP S/4HANA. Does your platform integrate with it?"})
    import time; time.sleep(3)
    state = get(f"/calls/{cid}")
    kinds = [c["kind"] for c in state["cards"]]
    check("API pipeline (call→inject→cards)", "integration" in kinds, f"cards={kinds}")
except Exception as e:
    check("API pipeline (call→inject→cards)", False, str(e))

# 3. Mistral SDK + key
try:
    import mistralai  # noqa
    from backend.app import config
    check("mistralai SDK installed", True, f"key set: {bool(config.MISTRAL_API_KEY)}")
    if config.MISTRAL_API_KEY:
        from mistralai import Mistral
        c = Mistral(api_key=config.MISTRAL_API_KEY)
        models = c.models.list()
        names = [m.id for m in models.data][:5]
        check("Mistral API reachable (models.list)", True, f"e.g. {names}")
except ImportError:
    check("mistralai SDK installed", False, "pip install mistralai (key IS set, SDK missing → mock mode)")
except Exception as e:
    check("Mistral API reachable (models.list)", False, str(e)[:120])

# 4. Google credentials + Meet API
cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
check("GOOGLE_APPLICATION_CREDENTIALS set", bool(cred and os.path.exists(cred)), cred or "not set")
if cred and os.path.exists(cred):
    try:
        from bot.meet_api import create_space
        space = create_space()
        check("Meet API v2 spaces.create", True, space.meeting_uri)
    except Exception as e:
        check("Meet API v2 spaces.create", False, str(e)[:160])
else:
    check("Meet API v2 spaces.create", False, "no credentials file")

# 5. Playwright + chromium
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        b.close()
    check("playwright chromium launches", True)
except ImportError:
    check("playwright chromium launches", False, "pip install playwright && playwright install chromium")
except Exception as e:
    check("playwright chromium launches", False, str(e)[:160])

# 6. chrome profile for signed-in Meet join — definitive test: open Meet with the
#    profile and check we do NOT land on the Google sign-in page
def _probe_profile():
    from playwright.sync_api import sync_playwright
    prof = os.getenv("LECLOSER_CHROME_PROFILE", "/tmp/lecloser-chrome-profile")
    args = ["--headless=new", "--use-fake-ui-for-media-stream",
            "--use-fake-device-for-media-stream", "--mute-audio", "--no-sandbox"]
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(prof, headless=True, args=args)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://meet.google.com/", wait_until="domcontentloaded", timeout=45000)
        import time
        time.sleep(5)
        title = page.title()
        url = page.url
        ctx.close()
        return "sign in" not in title.lower(), f"title='{title}' url={url[:60]}"

try:
    ok, detail = _probe_profile()
    check("chrome profile can open Meet without sign-in wall", ok,
          detail + " — if FAIL: sign in once (see RUNBOOK §4)")
except Exception as e:
    check("chrome profile can open Meet without sign-in wall", False, str(e)[:160])

print()
failed = [r for r in results if not r[1]]
print(f"{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
