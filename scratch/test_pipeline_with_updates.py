import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import re
import numpy as np
from PIL import Image

import cv_engine
import ocr_engine
import logic_engine
import executor

# Let's test the entire pipeline on the exact user image
img_path = r"C:\Users\Manasvi R\Downloads\Factorial Flowchart_ Input, Loop, Output.png"
pil_img = Image.open(img_path).convert("RGB")
img = cv_engine.normalize_image(pil_img)
blocks, thresh = cv_engine.detect_symbols(img)
connections, warnings = cv_engine.detect_connections(thresh, blocks)

print(f"1. Shapes detected: {len(blocks)}")
for b in blocks:
    print(f"  Shape {b['id']} ({b['type']}): bbox={b['bbox']}")

print(f"\n2. Connections detected: {len(connections)}")
for c in connections:
    print(f"  {c['from']} -> {c['to']}: conf={c['confidence']}, uncertain={c.get('uncertain')}")
