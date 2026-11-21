"""Pipeline test against the dev-dockerized backend (default http://localhost:8003)."""
import json
import os
import time
import urllib.request

BASE = os.getenv("LECLOSER_BACKEND", "http://localhost:8003")


def post(p, b):
    r = urllib.request.Request(BASE + p, data=json.dumps(b).encode(),
                               headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(r).read())


def get(p):
    return json.loads(urllib.request.urlopen(BASE + p).read())


c = post("/calls", {"client": {"company": "DockerDev GmbH", "country": "DE"},
                    "demo": True, "rep_name": "Alex"})
cid = c["call_id"]
post(f"/calls/{cid}/inject", {"speaker": "client",
     "text": "We run SAP S/4HANA — does it integrate? We have 300 users and need 25% discount."})
time.sleep(4)
s = get(f"/calls/{cid}")
print("rep_name:", s["rep_name"],
      "| cards:", [x["kind"] for x in s["cards"]],
      "| deal:", s["numbers"]["deal_value"] if s["numbers"] else None,
      "| flow:", s["flow"]["stage"])
print("OK")
