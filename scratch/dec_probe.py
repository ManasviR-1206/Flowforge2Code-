import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
import pytesseract

import cv_engine
import ocr_engine
import api_server

IMG = r"C:\Users\Manasvi R\Downloads\Largest of Three Numbers Flowchart.png"

with open(IMG, "rb") as f:
    raw = f.read()
img = cv_engine.normalize_image(api_server.pil_from_upload(raw))
blocks, _ = cv_engine.detect_symbols(img)
decisions = [b for b in blocks if b["type"] == "decision"]

for b in decisions:
    x, y, w, h = b["bbox"]
    print(f"\n########## decision #{b['id']} bbox={b['bbox']}")
    # Tight central crop to exclude the diamond outline
    cx1 = x + int(w * 0.20); cx2 = x + int(w * 0.80)
    cy1 = y + int(h * 0.18); cy2 = y + int(h * 0.82)
    for name, crop in (
        ("tight", img[cy1:cy2, cx1:cx2]),
        ("mid", img[y + int(h * 0.12):y + int(h * 0.88), x + int(w * 0.12):x + int(w * 0.88)]),
    ):
        cv2.imwrite(f"scratch/largest_dec{b['id']}_{name}.png", crop)
        g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        for fx in (3.0,):
            gs = cv2.resize(g, (0, 0), fx=fx, fy=fx, interpolation=cv2.INTER_CUBIC)
            for psm in (6, 4, 3, 11):
                txt = pytesseract.image_to_string(gs, config=f"--oem 3 --psm {psm}").strip().replace("\n", " | ")
                print(f"  [{name} x{fx} psm{psm}] {txt!r}")
        # boxes to look at operator glyphs
        box = pytesseract.image_to_boxes(gs).strip()
        print(f"  [{name} boxes] {box!r}")
