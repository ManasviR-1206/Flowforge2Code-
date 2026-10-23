import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
from PIL import Image
import cv_engine
import ocr_engine

img_path = r"C:\Users\Manasvi R\Downloads\Factorial Flowchart_ Input, Loop, Output.png"
with open(img_path, "rb") as f:
    pil_img = Image.open(f).convert("RGB")
img = cv_engine.normalize_image(pil_img)
blocks, thresh = cv_engine.detect_symbols(img)
connections, warnings = cv_engine.detect_connections(thresh, blocks)

print("Blocks:")
for b in blocks:
    print(f"ID {b['id']} ({b['type']}): bbox={b['bbox']}, center={b['center']}")

print("\nConnections:")
for c in connections:
    print(f"{c['from']} -> {c['to']}: vector={c['vector']}, conf={c['confidence']}, uncertain={c.get('uncertain')}")

# Now let's see what pytesseract sees in block 3, 4, 5
for bid in (3, 4, 5):
    b = next(x for x in blocks if x["id"] == bid)
    x, y, w, h = b["bbox"]
    crop = img[y:y+h, x:x+w]
    print(f"\n--- Block {bid} ({b['type']}) ---")
    d = ocr_engine.pytesseract.image_to_data(crop, output_type=ocr_engine.pytesseract.Output.DICT)
    words = [(t, c) for t, c in zip(d["text"], d["conf"]) if t.strip()]
    print("image_to_data words on raw crop:", words)
    raw_str = ocr_engine.pytesseract.image_to_string(crop)
    print("image_to_string on raw crop:\n" + repr(raw_str))

# Let's see where 'Yes' and 'No' are in the image!
full_data = ocr_engine.pytesseract.image_to_data(img, output_type=ocr_engine.pytesseract.Output.DICT)
for i, t in enumerate(full_data["text"]):
    if t.strip():
        print(f"Full image word: {repr(t)} at ({full_data['left'][i]}, {full_data['top'][i]}, {full_data['width'][i]}, {full_data['height'][i]}), conf={full_data['conf'][i]}")
