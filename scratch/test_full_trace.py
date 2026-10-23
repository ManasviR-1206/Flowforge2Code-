import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from fastapi.testclient import TestClient
from api_server import app

client = TestClient(app)
img_path = r"C:\Users\Manasvi R\Downloads\Factorial Flowchart_ Input, Loop, Output.png"
with open(img_path, "rb") as f:
    buf = f.read()

# 1. Analyze
res = client.post("/api/analyze", files={"file": ("factorial.png", buf, "image/png")})
print("Analyze status:", res.status_code)
data = res.json()

print("\n--- Nodes ---")
for n in data.get("nodes", []):
    print(" ", n["id"], n["type"], repr(n["data"]["label"]), "review:", n["data"].get("needs_review"), "conf:", n["data"].get("confidence"))

print("\n--- Edges ---")
for e in data.get("edges", []):
    print(" ", e["id"], f"{e['source']} -> {e['target']}", repr(e.get("label")), "uncertain:", e["data"].get("uncertain"))

print("\nGraph status:", data.get("graph_status"))
print("Warnings:", data.get("warnings"))

# 2. Generate Code
gen_res = client.post("/api/generate-code", json={"nodes": data["nodes"], "edges": data["edges"]})
print("\nGenerate-code status:", gen_res.status_code)
if gen_res.status_code == 200:
    code = gen_res.json()["code"]
    print("\n--- Generated Python Code ---")
    print(code)
    
    # 3. Execute with input 5
    exec5 = client.post("/api/execute", json={"code": code, "user_input": "5\n"})
    print("\nExecution for 5:", exec5.status_code, repr(exec5.json().get("program_output")), "Success:", exec5.json().get("success"))
    
    # 4. Execute with input 0
    exec0 = client.post("/api/execute", json={"code": code, "user_input": "0\n"})
    print("\nExecution for 0:", exec0.status_code, repr(exec0.json().get("program_output")), "Success:", exec0.json().get("success"))
else:
    print("Generate code error:", gen_res.text)
