import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))
import cv2

import api_server
from fastapi.testclient import TestClient
import test_stage2_image_upload as t

api_server.GEMINI_API_KEY = ""
client = TestClient(api_server.app)

image = t.build_synthetic_factorial_image()
_, encoded = cv2.imencode(".png", image)
r = client.post("/api/analyze", files={"file": ("factorial.png", encoded.tobytes(), "image/png")})
g = r.json()
print("graph_status:", g["graph_status"])
for n in g["nodes"]:
    print(f'  {n["id"]}: {n["data"]["label"]!r} needs_review={n["data"]["needs_review"]} uncertain={n["data"].get("uncertain")}')
