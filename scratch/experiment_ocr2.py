"""Experiment 2: interior-crop OCR preprocessing variants for tricky labels.

Targets: block 8 'fact = fact * i', block 9 'i = i + 1', block 3 'fact = 1'.
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


def interior(gray, top=0.18, bot=0.82, left=0.14, right=0.86):
    h, w = gray.shape[:2]
    return gray[int(h * top):int(h * bot), int(w * left):int(w * right)]


def variants(gray):
    out = {}
    inner = interior(gray)

    def up(g, fx):
        return cv2.resize(g, (0, 0), fx=fx, fy=fx, interpolation=cv2.INTER_CUBIC)

    for fx in (3.0, 4.0, 5.0):
        out[f"inner_gray_{int(fx)}x_psm6"] = ocr_engine._read_candidate(up(inner, fx), "--oem 3 --psm 6")
    out["inner_gray_4x_psm7"] = ocr_engine._read_candidate(up(inner, 4.0), "--oem 3 --psm 7")
    out["inner_gray_4x_psm8"] = ocr_engine._read_candidate(up(inner, 4.0), "--oem 3 --psm 8")
    out["inner_gray_4x_psm13"] = ocr_engine._read_candidate(up(inner, 4.0), "--oem 3 --psm 13")

    # adaptive on interior
    a = cv2.adaptiveThreshold(inner, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    out["inner_adapt_4x_psm6"] = ocr_engine._read_candidate(up(a, 4.0), "--oem 3 --psm 6")
    out["inner_adapt_4x_psm7"] = ocr_engine._read_candidate(up(a, 4.0), "--oem 3 --psm 7")

    # erode to remove thin border remnants, then otsu/adaptive
    try:
        dn = cv2.fastNlMeansDenoising(inner, None, 10, 7, 21)
        out["inner_denoise_4x_psm6"] = ocr_engine._read_candidate(up(dn, 4.0), "--oem 3 --psm 6")
        out["inner_denoise_4x_psm7"] = ocr_engine._read_candidate(up(dn, 4.0), "--oem 3 --psm 7")
    except Exception as e:
        out["denoise_error"] = (str(e), -1)

    # Otsu on interior
    _, o = cv2.threshold(inner, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    out["inner_otsu_4x_psm6"] = ocr_engine._read_candidate(up(o, 4.0), "--oem 3 --psm 6")
    out["inner_otsu_4x_psm7"] = ocr_engine._read_candidate(up(o, 4.0), "--oem 3 --psm 7")
    return out


def main():
    ocr_engine.init_tesseract()
    img = build_synthetic_factorial_image()
    norm = cv_engine.normalize_image(img)
    blocks, _ = cv_engine.detect_symbols(norm)

    for bid in (3, 4, 5, 8, 9):
        b = next(x for x in blocks if x["id"] == bid)
        x, y, bw, bh = b["bbox"]
        pad = max(6, int(round(min(bw, bh) * 0.12)))
        x1, y1 = max(0, x - pad), max(0, y - pad)
        x2, y2 = min(norm.shape[1], x + bw + pad), min(norm.shape[0], y + bh + pad)
        roi = norm[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        print(f"\n=== BLOCK #{bid} type={b['type']} ===")
        for name, (txt, conf) in variants(gray).items():
            print(f"   {name:<24} conf={conf:6.1f}  text={txt!r}")


if __name__ == "__main__":
    main()
