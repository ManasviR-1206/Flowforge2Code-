import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2

import api_server
from fastapi.testclient import TestClient

api_server.GEMINI_API_KEY = ""
client = TestClient(api_server.app)

IMG = r"C:\Users\Manasvi R\Downloads\Largest of Three Numbers Flowchart.png"
with open(IMG, "rb") as f:
    raw = f.read()

r = client.post("/api/analyze", files={"file": ("largest.png", raw, "image/png")})
print("analyze status:", r.status_code)
g = r.json()
print("graph_status:", g["graph_status"])
print("warnings:", g["warnings"])
for n in g["nodes"]:
    print(f'  node {n["id"]}: {n["data"]["label"]!r} needs_review={n["data"]["needs_review"]} conf={n["data"].get("confidence")}')
for e in g["edges"]:
    print(f'  edge {e["source"]}->{e["target"]} label={e["label"]!r} handle={e.get("sourceHandle")!r} uncertain={e["data"].get("uncertain")} unconfirmed={e["data"].get("unconfirmed_suggestion")}')

cc = client.post("/api/generate-code", json={"nodes": g["nodes"], "edges": g["edges"]})
print("generate-code status:", cc.status_code)
print("detail/code:", (cc.json().get("detail") or cc.json().get("code")) )
