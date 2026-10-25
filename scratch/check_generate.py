import sys, os, ast
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
import api_server

c = TestClient(api_server.app)
p = r"C:\Users\Manasvi R\Downloads\Largest of Three Numbers Flowchart.png"
with open(p, "rb") as f:
    data = f.read()
graph = c.post("/api/analyze", files={"file": ("a.png", data, "image/png")}).json()
gen = c.post("/api/generate-code", json={"nodes": graph["nodes"], "edges": graph["edges"]})
print("generate status", gen.status_code)
code = gen.json().get("code", "")
print(code)
ast.parse(code)
for inp, want in (("3\n7\n5\n", "B is largest"), ("9\n2\n4\n", "A is largest"), ("1\n2\n8\n", "C is largest"), ("5\n5\n5\n", "A is largest")):
    ex = c.post("/api/execute", json={"code": code, "user_input": inp})
    out = ex.json().get("output", "")
    ok = ex.json().get("success") and want in out
    print(f"  input={inp!r} -> expected {want!r}: {'OK' if ok else 'FAIL: ' + repr(out)}")
