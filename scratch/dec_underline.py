import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
import pytesseract

import cv_engine
import api_server

IMG = r"C:\Users\Manasvi R\Downloads\Largest of Three Numbers Flowchart.png"

with open(IMG, "rb") as f:
    raw = f.read()
img = cv_engine.normalize_image(api_server.pil_from_upload(raw))
blocks, _ = cv_engine.detect_symbols(img)
decisions = [b for b in blocks if b["type"] == "decision"]

for b in decisions:
    x, y, w, h = b["bbox"]
    for tag, cx1, cx2, cy1, cy2 in (
        ("tight", x + int(w * 0.20), x + int(w * 0.80), y + int(h * 0.18), y + int(h * 0.82)),
        ("full", x, x + w, y, y + h),
    ):
        crop = img[cy1:cy2, cx1:cx2]
        if crop.size == 0:
            continue
        g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        gs = cv2.resize(g, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        H = gs.shape[0]
        boxes = pytesseract.image_to_boxes(gs).strip()
        print(f"\n# dec {b['id']} {tag} (H={H})")
        for bline in boxes.splitlines():
            p = bline.split()
            if len(p) < 5:
                continue
            ch = p[0]
            if ch not in ("<", ">", "=", "2", "z"):
                continue
            l, bt, r, tt = int(p[1]), int(p[2]), int(p[3]), int(p[4])
            top = H - tt
            bot = H - bt
            ch_w = max(1, r - l)
            ch_h = max(1, bot - top)
            # bottom strip inside the box
            strip = gs[max(0, bot - max(2, int(ch_h * 0.28))):bot, l:r]
            if strip.size:
                _, bink = cv2.threshold(strip, 170, 255, cv2.THRESH_BINARY_INV)
                rows = np.sum(bink > 0, axis=1)
                frac = [round(float(c) / ch_w, 2) for c in rows]
                wide = any(c >= ch_w * 0.55 for c in rows)
                print(f"   ch={ch!r} box=({l},{bt},{r},{tt}) char_h={ch_h} bot_strip_rows_frac={frac} wide_underline={wide}")
