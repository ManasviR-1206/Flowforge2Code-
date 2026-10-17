import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import pytesseract

import cv_engine
import ocr_engine
import api_server

IMG = r"C:\Users\Manasvi R\Downloads\Largest of Three Numbers Flowchart.png"
with open(IMG, "rb") as f:
    raw = f.read()
img = cv_engine.normalize_image(api_server.pil_from_upload(raw))
blocks, _ = cv_engine.detect_symbols(img)

for b in blocks:
    if b["type"] != "decision":
        continue
    x, y, w, h = b["bbox"]
    img_h, img_w = img.shape[:2]
    shape_x1 = min(img_w, x + int(w * 0.12)); shape_y1 = min(img_h, y + int(h * 0.2))
    shape_x2 = max(shape_x1, min(img_w, x + int(w * 0.88))); shape_y2 = max(shape_y1, min(img_h, y + int(h * 0.8)))
    shape_inner = img[shape_y1:shape_y2, shape_x1:shape_x2]
    exact_box = img[y:y+h, x:x+w]
    print(f"\n### decision {b['id']} bbox={b['bbox']}")
    for name, crop in (("shape_inner", shape_inner), ("exact_box", exact_box)):
        cg = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        bs = pytesseract.image_to_boxes(cg).strip()
        print(f"  {name} boxes: {bs!r}")
        for bline in bs.splitlines():
            parts = bline.split()
            if len(parts) >= 5 and parts[0] in ("<", ">"):
                bt = (parts[0], int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]))
                print(f"    op {parts[0]} underline={ocr_engine.check_underline_under_operator(cg, bt)}")
