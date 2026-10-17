import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
import api_server

c = TestClient(api_server.app)
p = r"C:\Users\Manasvi R\Downloads\Largest of Three Numbers Flowchart.png"
with open(p, "rb") as f:
    data = f.read()
r = c.post("/api/analyze", files={"file": ("a.png", data, "image/png")})
print("status", r.status_code)
j = r.json()
print("graph_status", j.get("graph_status"))
print("warnings", j.get("warnings"))
for n in j["nodes"]:
    d = n["data"]
    print(f"  node {n['id']:>3} {n['type']:<10} review={str(d.get('needs_review')):<5} conf={d.get('confidence'):>6} label={d.get('label')!r}")
print("edges:")
for e in j["edges"]:
    print(f"  {e['source']}->{e['target']} label={e.get('label')!r} unc={e.get('style', {}).get('strokeDasharray')}")
