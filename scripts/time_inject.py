"""Time one /inject call (router → real Mistral Small) to see live latency."""
import json
import time
import urllib.request

BASE = "http://localhost:8003"


def post(path, body, timeout=90):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def get(path):
    return json.loads(urllib.request.urlopen(BASE + path, timeout=10).read())


call = post("/calls", {"client": {"company": "Timing GmbH", "country": "DE"}, "demo": True})
cid = call["call_id"]
t0 = time.time()
post(f"/calls/{cid}/inject", {"speaker": "client",
     "text": "We run SAP S/4HANA. Does your platform integrate with it? And we have about 300 users."})
t1 = time.time()
print(f"inject (router + fast agents) took {t1 - t0:.1f}s")
time.sleep(4)
state = get(f"/calls/{cid}")
for c in state["cards"]:
    print(f"  card [{c['kind']}] {c['title']}: {c['body'][:100]}")
print("numbers:", state["numbers"])
