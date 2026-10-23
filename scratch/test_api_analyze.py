import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from fastapi.testclient import TestClient
from api_server import app

client = TestClient(app)
img_path = r"C:\Users\Manasvi R\Downloads\Factorial Flowchart_ Input, Loop, Output.png"
with open(img_path, "rb") as f:
    buf = f.read()

res = client.post("/api/analyze", files={"file": ("factorial.png", buf, "image/png")})
print("Analyze status:", res.status_code)
data = res.json()
print("Nodes:")
for n in data.get("nodes", []):
    print(" ", n["id"], n["type"], repr(n["data"]["label"]), n["data"].get("needs_review"))

print("Edges:")
for e in data.get("edges", []):
    print(" ", e["id"], f"{e['source']} -> {e['target']}", repr(e.get("label")), e["data"].get("uncertain"), e["data"].get("unconfirmed_suggestion"))

print("Graph status:", data.get("graph_status"))
print("Warnings:", data.get("warnings"))
