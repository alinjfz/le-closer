import json, time, urllib.request

BASE = "http://localhost:8003"

def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req).read())

def get(path):
    return json.loads(urllib.request.urlopen(BASE + path).read())

c = post("/calls", {"client": {"company": "Proto GmbH"}, "demo": True})
cid = c["call_id"]
post(f"/calls/{cid}/inject", {"speaker": "client", "text": "We use SAP S/4HANA. Does your platform integrate?"})
time.sleep(3)
s = get(f"/calls/{cid}")
for card in s["cards"]:
    if card["kind"] == "integration":
        print("integration card meta:", card["meta"])
r = post(f"/calls/{cid}/prototype", {"topic": "SAP integration"})
print("prototype POST:", "ok" if r.get("ok") else r, "| html len:", len(r.get("prototype", {}).get("html", "")))
s = get(f"/calls/{cid}")
print("prototypes in state:", len(s["prototypes"]), s["prototypes"][0]["title"] if s["prototypes"] else "")
