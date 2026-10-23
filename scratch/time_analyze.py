import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
import api_server, ocr_engine

d = open(r"C:\Users\Manasvi R\Downloads\Largest of Three Numbers Flowchart.png", "rb").read()

orig = ocr_engine.recover_condition_operators
ocr_engine.recover_condition_operators = lambda text, roi: text
c = TestClient(api_server.app)
t = time.time(); r = c.post("/api/analyze", files={"file": ("a.png", d, "image/png")})
print("WITHOUT repair:", round(time.time() - t, 2), "s", r.json()["graph_status"])

ocr_engine.recover_condition_operators = orig
c2 = TestClient(api_server.app)
t = time.time(); r2 = c2.post("/api/analyze", files={"file": ("a.png", d, "image/png")})
print("WITH repair:   ", round(time.time() - t, 2), "s", r2.json()["graph_status"])

# time the signature read alone for the two decisions
import cv_engine
img = cv_engine.normalize_image(api_server.pil_from_upload(d))
blocks, _ = cv_engine.detect_symbols(img)
for b in blocks:
    if b["type"] != "decision":
        continue
    x, y, w, h = b["bbox"]
    t = time.time()
    sigs = ocr_engine.read_condition_operator_signatures(img[y:y + h, x:x + w], expected_count=2)
    print(f"  sig-read dec{b['id']}: {round(time.time()-t,2)}s  ({len(sigs)} probes)")
