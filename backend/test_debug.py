import json, time, urllib.request

def post(path, body):
    req = urllib.request.Request("http://localhost:8003" + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req).read())

def get(path):
    return json.loads(urllib.request.urlopen("http://localhost:8003" + path).read())

c = post("/calls", {"client": {"company": "X"}, "demo": True})
cid = c["call_id"]
post(f"/calls/{cid}/inject", {"speaker": "client", "text": "We run everything on SAP S/4HANA. Does your platform integrate with it?"})
time.sleep(3)
s = get(f"/calls/{cid}")
print("cards:", [(x["kind"], x["title"]) for x in s["cards"]])
print("activity:", [(a["agent"], a["message"][:70], a["status"]) for a in s["activity"]])
