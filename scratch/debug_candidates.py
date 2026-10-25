import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
from PIL import Image
import cv_engine
import ocr_engine

img_path = r"C:\Users\Manasvi R\Downloads\Factorial Flowchart_ Input, Loop, Output.png"
pil_img = Image.open(img_path).convert("RGB")
img = cv_engine.normalize_image(pil_img)

blocks, thresh = cv_engine.detect_symbols(img)
b3 = next(x for x in blocks if x["id"] == 3)
b4 = next(x for x in blocks if x["id"] == 4)
b5 = next(x for x in blocks if x["id"] == 5)

for b in (b3, b4, b5):
    print(f"\n=================== BLOCK {b['id']} ({b['type']}) ===================")
    x, y, w, h = b["bbox"]
    img_h, img_w = img.shape[:2]
    pad = max(6, int(round(min(w, h) * 0.12)))
    x1, y1 = max(0, x - pad), max(0, y - pad)
    x2, y2 = min(img_w, x + w + pad), min(img_h, y + h + pad)
    roi = img[y1:y2, x1:x2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    
    # Let's inspect each candidate
    full_size = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    t1, c1 = ocr_engine._read_candidate(full_size, "--oem 3 --psm 6")
    print(f"Candidate 1 (full_size psm 6): text={repr(t1)}, conf={c1}")

    height, width = gray.shape[:2]
    inner = gray[int(height * 0.2):int(height * 0.8), int(width * 0.16):int(width * 0.84)]
    if inner.size:
        inner_size = cv2.resize(inner, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        t2, c2 = ocr_engine._read_candidate(inner_size, "--oem 3 --psm 6")
        print(f"Candidate 2 (inner_size psm 6): text={repr(t2)}, conf={c2}")

    adaptive = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    adaptive_size = cv2.resize(
        adaptive, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC
    )
    t3, c3 = ocr_engine._read_candidate(adaptive_size, "--oem 3 --psm 11")
    print(f"Candidate 3 (adaptive_size psm 11): text={repr(t3)}, conf={c3}")

    shape_x1 = min(img_w, x + int(w * 0.12))
    shape_y1 = min(img_h, y + int(h * 0.2))
    shape_x2 = max(shape_x1, min(img_w, x + int(w * 0.88)))
    shape_y2 = max(shape_y1, min(img_h, y + int(h * 0.8)))
    shape_inner = img[shape_y1:shape_y2, shape_x1:shape_x2]
    if shape_inner.size:
        shape_gray = cv2.cvtColor(shape_inner, cv2.COLOR_BGR2GRAY)
        shape_gray_size = cv2.resize(
            shape_gray, (0, 0), fx=3.0, fy=3.0,
            interpolation=cv2.INTER_CUBIC,
        )
        t4, c4 = ocr_engine._read_candidate(shape_gray_size, "--oem 3 --psm 6")
        print(f"Candidate 4 (shape_gray_size psm 6): text={repr(t4)}, conf={c4}")
