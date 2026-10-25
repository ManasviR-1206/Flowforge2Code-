import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
from PIL import Image

import cv_engine
import ocr_engine
import logic_engine
import api_server

img_path = r"C:\Users\Manasvi R\Downloads\Factorial Flowchart_ Input, Loop, Output.png"
print("File exists:", os.path.exists(img_path))

with open(img_path, "rb") as f:
    raw_bytes = f.read()

# Simulate api_server analyze
pil_img = api_server.pil_from_upload(raw_bytes)
img = cv_engine.normalize_image(pil_img)
print(f"Normalized image shape: {img.shape}")

blocks, thresh = cv_engine.detect_symbols(img)
print(f"Detected {len(blocks)} blocks:")
for b in blocks:
    text, conf = ocr_engine.extract_block_text_with_confidence(img, b["bbox"])
    print(f"  Block {b['id']}: type={b['type']}, bbox={b['bbox']}, conf={conf:.1f}, text={repr(text)}")

connections, warnings = cv_engine.detect_connections(thresh, blocks)
print(f"Detected {len(connections)} connections:")
for c in connections:
    print(f"  Connection: {c['from']} -> {c['to']}, conf={c['confidence']}, uncertain={c.get('uncertain')}, branch={repr(c.get('branch'))}")

print("Warnings:", warnings)
