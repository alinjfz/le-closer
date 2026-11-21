"""Quick end-to-end test of the backend pipeline (no audio, uses /inject)."""
import json
import time
import urllib.request

BASE = "http://localhost:8000"


def post(path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    return json.loads(urllib.request.urlopen(req).read())


def get(path):
    return json.loads(urllib.request.urlopen(BASE + path).read())


call = post("/calls", {"client": {"company": "Müller Logistik GmbH", "country": "DE",
                                   "people": [{"name": "Dr. Anna Weber", "title": "Head of IT"}]},
                        "demo": True})
cid = call["call_id"]
print("call:", cid)

post(f"/calls/{cid}/inject", {"speaker": "client",
     "text": "We run everything on SAP S/4HANA. Does your platform integrate with it?"})
time.sleep(3)
post(f"/calls/{cid}/inject", {"speaker": "rep",
     "text": "I'll send you the security document this week."})
post(f"/calls/{cid}/inject", {"speaker": "client",
     "text": "We are about 300 users and would need at least 25% discount."})
post(f"/calls/{cid}/inject", {"speaker": "client",
     "text": "We have detailed questions on GDPR and data hosting. Where is your data hosted?"})
time.sleep(2)

state = get(f"/calls/{cid}")
print("segments:", len(state["segments"]))
print("cards:", [(c["kind"], c["title"]) for c in state["cards"]])
print("tasks:", [(t["title"][:40], t["status"]) for t in state["tasks"]])
print("numbers:", state["numbers"])
print("flow:", state["flow"])
print("mindmap lines:", len(state["mindmap_md"].splitlines()))
print("activity:", [(a["agent"], a["status"]) for a in state["activity"][-6:]])

post(f"/calls/{cid}/end", {})
time.sleep(2)
notes = get(f"/calls/{cid}/notes")
print("followup status:", notes["followup_status"])
post(f"/calls/{cid}/followup/decision", {"decision": "approve"})
time.sleep(2)
notes = get(f"/calls/{cid}/notes")
print("after approve:", notes["followup_status"])
print("OK")
