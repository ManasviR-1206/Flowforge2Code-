"""Diagnostic: print ALL OCR candidates per block for the synthetic factorial image.

Synthetic-only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
import cv_engine
import ocr_engine

from tests.test_stage2_image_upload import build_synthetic_factorial_image


def all_candidates(img, bbox):
    x, y, w, h = bbox
    img_h, img_w = img.shape[:2]
    pad = max(6, int(round(min(w, h) * 0.12)))
    x1, y1 = max(0, x - pad), max(0, y - pad)
    x2, y2 = min(img_w, x + w + pad), min(img_h, y + h + pad)
    roi = img[y1:y2, x1:x2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    out = []
    full_size = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    out.append(("full_2x_psm6", ocr_engine._read_candidate(full_size, "--oem 3 --psm 6")))
    height, width = gray.shape[:2]
    inner = gray[int(height * 0.2):int(height * 0.8), int(width * 0.16):int(width * 0.84)]
    if inner.size:
        inner_size = cv2.resize(inner, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        out.append(("inner_3x_psm6", ocr_engine._read_candidate(inner_size, "--oem 3 --psm 6")))
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    adaptive_size = cv2.resize(adaptive, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    out.append(("adaptive_2x_psm11", ocr_engine._read_candidate(adaptive_size, "--oem 3 --psm 11")))
    shape_x1 = min(img_w, x + int(w * 0.12))
    shape_y1 = min(img_h, y + int(h * 0.2))
    shape_x2 = max(shape_x1, min(img_w, x + int(w * 0.88)))
    shape_y2 = max(shape_y1, min(img_h, y + int(h * 0.8)))
    shape_inner = img[shape_y1:shape_y2, shape_x1:shape_x2]
    if shape_inner.size:
        shape_gray = cv2.cvtColor(shape_inner, cv2.COLOR_BGR2GRAY)
        shape_gray_size = cv2.resize(shape_gray, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        out.append(("shapeinner_3x_psm6", ocr_engine._read_candidate(shape_gray_size, "--oem 3 --psm 6")))
        if min(shape_gray.shape[:2]) >= 11:
            shape_adaptive = cv2.adaptiveThreshold(shape_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            shape_size = cv2.resize(shape_adaptive, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
            out.append(("shapeinner_adaptive_3x_psm11", ocr_engine._read_candidate(shape_size, "--oem 3 --psm 11")))
    return out


def main():
    ocr_engine.init_tesseract()
    img = build_synthetic_factorial_image()
    norm = cv_engine.normalize_image(img)
    blocks, _ = cv_engine.detect_symbols(norm)
    for b in blocks:
        print(f"\n=== BLOCK #{b['id']} type={b['type']} bbox={b['bbox']} ===")
        for name, (txt, conf) in all_candidates(norm, b["bbox"]):
            print(f"   {name:<28} conf={conf:6.1f}  text={txt!r}")


if __name__ == "__main__":
    main()
