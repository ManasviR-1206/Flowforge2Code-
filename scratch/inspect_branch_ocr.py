import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
from PIL import Image
import cv_engine
import ocr_engine

img_path = r"C:\Users\Manasvi R\Downloads\Factorial Flowchart_ Input, Loop, Output.png"
pil_img = Image.open(img_path).convert("RGB")
img = cv_engine.normalize_image(pil_img)
blocks, thresh = cv_engine.detect_symbols(img)
connections, warnings = cv_engine.detect_connections(thresh, blocks)

# Let's inspect where Yes and No are located near Block 4
# Block 4: bbox=(366, 663, 284, 195)
b4 = next(b for b in blocks if b["id"] == 4)
print("Block 4 bbox:", b4["bbox"])

# Check all text around Block 4
x, y, w, h = b4["bbox"]
surround = img[max(0, y-80):min(img.shape[0], y+h+80), max(0, x-150):min(img.shape[1], x+w+150)]
d = ocr_engine.pytesseract.image_to_data(surround, output_type=ocr_engine.pytesseract.Output.DICT)
for i, t in enumerate(d["text"]):
    if t.strip():
        print(f"Around decision: word={repr(t)}, conf={d['conf'][i]}, box=({d['left'][i]}, {d['top'][i]}, {d['width'][i]}, {d['height'][i]})")

# Also let's check connection 4->5 and 4->6
for c in connections:
    if c["from"] == 4:
        print(f"Conn from 4 to {c['to']}: vector={c['vector']}, branch={repr(c.get('branch'))}, conf={c.get('confidence')}, uncertain={c.get('uncertain')}")
