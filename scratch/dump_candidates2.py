import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np

import cv_engine
import ocr_engine
import api_server


def dump_candidates(img, bbox, block_id):
    x, y, w, h = bbox
    img_h, img_w = img.shape[:2]
    pad = max(6, int(round(min(w, h) * 0.12)))
    x1, y1 = max(0, x - pad), max(0, y - pad)
    x2, y2 = min(img_w, x + w + pad), min(img_h, y + h + pad)
    roi = img[y1:y2, x1:x2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    candidates = []
    full_size = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    candidates.append(("full psm6", _r(full_size, "--oem 3 --psm 6")))
    candidates.append(("full str psm6", _rs(full_size, "--oem 3 --psm 6")))
    candidates.append(("full psm4", _r(full_size, "--oem 3 --psm 4")))
    height, width = gray.shape[:2]
    inner = gray[int(height * 0.2):int(height * 0.8), int(width * 0.16):int(width * 0.84)]
    if inner.size:
        inner_size = cv2.resize(inner, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        candidates.append(("inner psm6", _r(inner_size, "--oem 3 --psm 6")))
        candidates.append(("inner str psm6", _rs(inner_size, "--oem 3 --psm 6")))
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    adaptive_size = cv2.resize(adaptive, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    candidates.append(("adaptive psm11", _r(adaptive_size, "--oem 3 --psm 11")))
    candidates.append(("adaptive psm12", _r(adaptive_size, "--oem 3 --psm 12")))
    shape_x1 = min(img_w, x + int(w * 0.12))
    shape_y1 = min(img_h, y + int(h * 0.2))
    shape_x2 = max(shape_x1, min(img_w, x + int(w * 0.88)))
    shape_y2 = max(shape_y1, min(img_h, y + int(h * 0.8)))
    shape_inner = img[shape_y1:shape_y2, shape_x1:shape_x2]
    if shape_inner.size:
        shape_gray = cv2.cvtColor(shape_inner, cv2.COLOR_BGR2GRAY)
        shape_gray_size = cv2.resize(shape_gray, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        candidates.append(("shapeinner psm6", _r(shape_gray_size, "--oem 3 --psm 6")))
        candidates.append(("shapeinner str psm6", _rs(shape_gray_size, "--oem 3 --psm 6")))
        if min(shape_gray.shape[:2]) >= 11:
            sa = cv2.adaptiveThreshold(shape_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            ss = cv2.resize(sa, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
            candidates.append(("shapeinner psm11", _r(ss, "--oem 3 --psm 11")))
            candidates.append(("shapeinner psm12", _r(ss, "--oem 3 --psm 12")))
    exact_box = img[y:y+h, x:x+w]
    if exact_box.size:
        exact_gray = cv2.cvtColor(exact_box, cv2.COLOR_BGR2GRAY)
        candidates.append(("exact psm6", _r(exact_gray, "--oem 3 --psm 6")))
        candidates.append(("exact str psm6", _rs(exact_gray, "--oem 3 --psm 6")))
        candidates.append(("exact psm11", _r(exact_gray, "--oem 3 --psm 11")))

    print(f"===== Block {block_id} bbox={bbox} =====")
    for name, (raw, conf) in candidates:
        cleaned = ocr_engine.clean_ocr_text(raw)
        print(f"  [{name}] conf={conf:.1f}\n     raw={raw!r}\n     clean={cleaned!r}")


def _r(image, config):
    return ocr_engine._read_candidate(image, config)


def _rs(image, config):
    return ocr_engine._read_candidate_string(image, config)


with open(r"C:\Users\Manasvi R\Downloads\Even or Odd Flowchart.png", "rb") as f:
    raw_bytes = f.read()
pil_img = api_server.pil_from_upload(raw_bytes)
img = cv_engine.normalize_image(pil_img)
blocks, thresh = cv_engine.detect_symbols(img)
for b in blocks:
    if b["id"] in (2, 3, 4, 5):
        dump_candidates(img, b["bbox"], b["id"])
        for b2 in blocks:
            if b2["id"] == b["id"]:
                t, c = ocr_engine.extract_block_text_with_confidence(img, b["bbox"])
                print(f"  >>> CHOSEN: conf={c} text={t!r}")
