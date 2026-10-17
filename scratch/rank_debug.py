import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import re
import cv2
import numpy as np

import cv_engine
import ocr_engine
import api_server

# monkeypatch the ranking to log
_orig_max = max


def candidate_rank(candidate):
    raw_text, confidence = candidate
    cleaned = ocr_engine.clean_ocr_text(raw_text)
    rank = confidence
    if re.search(r"\b(?:input|print|start|end)\b", cleaned, re.I):
        rank += 18
    if re.search(r"\b[A-Za-z_]\w*\s*=\s*[^=].+", cleaned):
        rank += 18
    if re.search(r"(?:<=|>=|==|!=|[<>])", cleaned):
        rank += 12
    if len(re.findall(r"[A-Za-z0-9]", cleaned)) >= 3:
        rank += 6
    if "\n" in cleaned:
        sub_lines = [l.strip() for l in cleaned.splitlines() if l.strip()]
        if len(sub_lines) >= 2 and all(re.search(r"\b[A-Za-z_]\w*\s*=", l) for l in sub_lines):
            rank += 30
    return rank


with open(r"C:\Users\Manasvi R\Downloads\Even or Odd Flowchart.png", "rb") as f:
    raw_bytes = f.read()
img = cv_engine.normalize_image(api_server.pil_from_upload(raw_bytes))
blocks, _ = cv_engine.detect_symbols(img)
bbox = next(b["bbox"] for b in blocks if b["id"] == 3)

# Rebuild the candidate list exactly as extract_block_text_with_confidence does
x, y, w, h = bbox
img_h, img_w = img.shape[:2]
pad = max(6, int(round(min(w, h) * 0.12)))
x1, y1 = max(0, x - pad), max(0, y - pad)
x2, y2 = min(img_w, x + w + pad), min(img_h, y + h + pad)
roi = img[y1:y2, x1:x2]
gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
candidates = []
full_size = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
candidates.append(_read := ocr_engine._read_candidate(full_size, "--oem 3 --psm 6"))
candidates.append(ocr_engine._read_candidate_string(full_size, "--oem 3 --psm 6"))
candidates.append(ocr_engine._read_candidate(full_size, "--oem 3 --psm 4"))
height, width = gray.shape[:2]
inner = gray[int(height * 0.2):int(height * 0.8), int(width * 0.16):int(width * 0.84)]
if inner.size:
    inner_size = cv2.resize(inner, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    candidates.append(ocr_engine._read_candidate(inner_size, "--oem 3 --psm 6"))
    candidates.append(ocr_engine._read_candidate_string(inner_size, "--oem 3 --psm 6"))
adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
adaptive_size = cv2.resize(adaptive, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
candidates.append(ocr_engine._read_candidate(adaptive_size, "--oem 3 --psm 11"))
candidates.append(ocr_engine._read_candidate(adaptive_size, "--oem 3 --psm 12"))
shape_x1 = min(img_w, x + int(w * 0.12)); shape_y1 = min(img_h, y + int(h * 0.2))
shape_x2 = max(shape_x1, min(img_w, x + int(w * 0.88))); shape_y2 = max(shape_y1, min(img_h, y + int(h * 0.8)))
shape_inner = img[shape_y1:shape_y2, shape_x1:shape_x2]
if shape_inner.size:
    shape_gray = cv2.cvtColor(shape_inner, cv2.COLOR_BGR2GRAY)
    shape_gray_size = cv2.resize(shape_gray, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    candidates.append(ocr_engine._read_candidate(shape_gray_size, "--oem 3 --psm 6"))
    candidates.append(ocr_engine._read_candidate_string(shape_gray_size, "--oem 3 --psm 6"))
    if min(shape_gray.shape[:2]) >= 11:
        shape_adaptive = cv2.adaptiveThreshold(shape_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        shape_size = cv2.resize(shape_adaptive, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        candidates.append(ocr_engine._read_candidate(shape_size, "--oem 3 --psm 11"))
        candidates.append(ocr_engine._read_candidate(shape_size, "--oem 3 --psm 12"))
exact_box = img[y:y+h, x:x+w]
if exact_box.size:
    exact_gray = cv2.cvtColor(exact_box, cv2.COLOR_BGR2GRAY)
    candidates.append(ocr_engine._read_candidate(exact_gray, "--oem 3 --psm 6"))
    candidates.append(ocr_engine._read_candidate_string(exact_gray, "--oem 3 --psm 6"))
    candidates.append(ocr_engine._read_candidate(exact_gray, "--oem 3 --psm 11"))

print("idx rank conf clean  raw")
for i, c in enumerate(candidates):
    print(f"{i:2d}  rank={candidate_rank(c):6.1f} conf={c[1]:6.1f} raw={c[0]!r} clean={ocr_engine.clean_ocr_text(c[0])!r}")

best = max(candidates, key=candidate_rank)
print("BEST:", best, "rank", candidate_rank(best))
