import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np

import cv_engine
import api_server

IMG = r"C:\Users\Manasvi R\Downloads\Largest of Three Numbers Flowchart.png"

with open(IMG, "rb") as f:
    raw = f.read()
img = cv_engine.normalize_image(api_server.pil_from_upload(raw))
h, w = img.shape[:2]
print("shape", img.shape)

params = cv_engine.get_adaptive_params(h, w)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
blurred = cv2.GaussianBlur(gray, params["k_blur"], 0)
thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, params["k_thresh_block"], 2)
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, params["k_morph"])
closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
cv2.imwrite("scratch/largest_thresh.png", thresh)
cv2.imwrite("scratch/largest_closed.png", closed)

contours, hierarchy = cv2.findContours(closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
img_area = h * w
min_area = max(400 * (params["scale"] ** 2), img_area * 0.0008)
print("scale", round(params["scale"], 3), "min_area", round(min_area, 1))

raw_blocks = []
for cnt in contours:
    area = cv2.contourArea(cnt)
    if area < min_area or area > img_area * 0.85:
        continue
    peri = cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
    x, y, bw, bh = cv2.boundingRect(cnt)
    ar = bw / max(1, bh)
    circ = (4 * np.pi * area) / (peri * peri) if peri > 0 else 0
    st = cv_engine.classify_shape(approx, cnt, ar, circ)
    min_symbol_dim = max(12, int(round(18 * params["scale"])))
    drop_textglyph = min(bw, bh) < min_symbol_dim and st not in ("connector", "offpage")
    raw_blocks.append({
        "id": len(raw_blocks) + 1, "type": st, "bbox": (x, y, bw, bh),
        "center": (x + bw // 2, y + bh // 2), "area": area, "verts": len(approx),
    })
    print(f"  raw#{len(raw_blocks):2d} verts={len(approx)} type={st:12s} area={area:9.0f} bbox=({x},{y},{bw},{bh}) ar={ar:.2f} circ={circ:.2f} glyph_drop={drop_textglyph}")

kept = cv_engine.filter_overlapping_blocks(raw_blocks)
print("after filter_overlapping_blocks:", len(kept))
for b in kept:
    print(f"  kept#{b['id']:2d} type={b['type']:12s} bbox={b['bbox']} area={b['area']:.0f}")

blocks, _ = cv_engine.detect_symbols(img)
overlay = cv_engine.overlay_detections(img, blocks, [])
cv2.imwrite("scratch/largest_overlay.png", overlay)
print("wrote scratch/largest_thresh.png, largest_closed.png, largest_overlay.png")
