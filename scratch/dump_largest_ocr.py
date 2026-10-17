import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np

import cv_engine
import ocr_engine
import api_server

IMG = r"C:\Users\Manasvi R\Downloads\Largest of Three Numbers Flowchart.png"


def _rc(image, config):
    return ocr_engine._read_candidate(image, config)


def _rs(image, config):
    return ocr_engine._read_candidate_string(image, config)


def dump(img, bbox, label):
    x, y, w, h = bbox
    img_h, img_w = img.shape[:2]
    pad = max(6, int(round(min(w, h) * 0.12)))
    x1, y1 = max(0, x - pad), max(0, y - pad)
    x2, y2 = min(img_w, x + w + pad), min(img_h, y + h + pad)
    roi = img[y1:y2, x1:x2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    defs = []
    full = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    defs.append(("full psm6", _rc(full, "--oem 3 --psm 6")))
    defs.append(("full psm6 str", _rs(full, "--oem 3 --psm 6")))
    defs.append(("full psm4", _rc(full, "--oem 3 --psm 4")))
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    adaptive_size = cv2.resize(adaptive, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    defs.append(("adaptive psm11", _rc(adaptive_size, "--oem 3 --psm 11")))
    defs.append(("adaptive psm12", _rc(adaptive_size, "--oem 3 --psm 12")))
    height, width = gray.shape[:2]
    inner = gray[int(height * 0.2):int(height * 0.8), int(width * 0.16):int(width * 0.84)]
    if inner.size:
        ist = cv2.resize(inner, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        defs.append(("inner psm6", _rc(ist, "--oem 3 --psm 6")))
        defs.append(("inner psm6 str", _rs(ist, "--oem 3 --psm 6")))
    shape_x1 = min(img_w, x + int(w * 0.12)); shape_y1 = min(img_h, y + int(h * 0.2))
    shape_x2 = max(shape_x1, min(img_w, x + int(w * 0.88))); shape_y2 = max(shape_y1, min(img_h, y + int(h * 0.8)))
    si = img[shape_y1:shape_y2, shape_x1:shape_x2]
    if si.size:
        sg = cv2.resize(cv2.cvtColor(si, cv2.COLOR_BGR2GRAY), (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        defs.append(("shapeinner psm6", _rc(sg, "--oem 3 --psm 6")))
        defs.append(("shapeinner psm6 str", _rs(sg, "--oem 3 --psm 6")))
        if min(si.shape[:2]) >= 11:
            sa = cv2.adaptiveThreshold(cv2.cvtColor(si, cv2.COLOR_BGR2GRAY), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            ss = cv2.resize(sa, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
            defs.append(("shapeinner psm11", _rc(ss, "--oem 3 --psm 11")))
            defs.append(("shapeinner psm12", _rc(ss, "--oem 3 --psm 12")))
    exact = gray
    defs.append(("exact psm6", _rc(exact, "--oem 3 --psm 6")))
    defs.append(("exact psm6 str", _rs(exact, "--oem 3 --psm 6")))
    defs.append(("exact psm11", _rc(exact, "--oem 3 --psm 11")))

    print(f"===== {label} bbox={bbox} =====")
    for name, (raw, conf) in defs:
        print(f"  [{name:18s}] conf={conf:6.1f} clean={ocr_engine.clean_ocr_text(raw)!r:40s} raw={raw!r}")
    t, c = ocr_engine.extract_block_text_with_confidence(img, bbox)
    print(f"  >>> CHOSEN conf={c} text={t!r}")


with open(IMG, "rb") as f:
    raw = f.read()
img = cv_engine.normalize_image(api_server.pil_from_upload(raw))
blocks, thresh = cv_engine.detect_symbols(img)
by_type = {}
for b in blocks:
    by_type.setdefault(b["type"], []).append(b)
for b in blocks:
    dump(img, b["bbox"], f"#{b['id']} {b['type']}")
