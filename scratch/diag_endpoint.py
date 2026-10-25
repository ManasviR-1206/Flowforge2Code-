import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from fastapi.testclient import TestClient
from api_server import app

client = TestClient(app)

with open(r"C:\Users\Manasvi R\Downloads\Even or Odd Flowchart.png", "rb") as f:
    raw = f.read()

res = client.post("/api/analyze", files={"file": ("even_odd.png", raw, "image/png")})
print("analyze status:", res.status_code)
data = res.json()
print("graph_status:", data.get("graph_status"))
print("missing_connections:", data.get("missing_connections"))
print("warning:", data.get("warning"))
print("nodes:")
for n in data["nodes"]:
    print(f"  {n['id']}: {n['type']:12s} label={n['data']['label']!r:24s} needs_review={n['data']['needs_review']}")
print("edges:")
for e in data["edges"]:
    print(f"  {e['source']} -> {e['target']} label={e['label']!r:6s} sourceHandle={e.get('sourceHandle')!r} uncertain={e['data']['uncertain']} unconfirmed={e['data'].get('unconfirmed_suggestion')}")

gen = client.post("/api/generate-code", json={"nodes": data["nodes"], "edges": data["edges"]})
print("generate-code status:", gen.status_code)
if gen.status_code == 200:
    print(gen.json()["code"])
else:
    print(gen.json())
