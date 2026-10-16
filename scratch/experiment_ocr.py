"""Experiment: which OCR preprocessing reads the tricky labels correctly?

Targets: block 8 'fact = fact * i', block 9 'i = i + 1'.
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


def variants(gray):
    out = {}
    h, w = gray.shape[:2]

    def otsu(g):
        _, b = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return b

    def upscale(g, fx):
        return cv2.resize(g, (0, 0), fx=fx, fy=fx, interpolation=cv2.INTER_CUBIC)

    # grayscale at various scales
    for fx in (2.0, 3.0, 4.0):
        out[f"gray_{int(fx)}x_psm6"] = ocr_engine._read_candidate(upscale(gray, fx), "--oem 3 --psm 6")
    # otsu
    o = otsu(gray)
    for fx in (2.0, 3.0, 4.0):
        out[f"otsu_{int(fx)}x_psm6"] = ocr_engine._read_candidate(upscale(o, fx), "--oem 3 --psm 6")
    # adaptive (current)
    a = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    for fx in (2.0, 3.0):
        out[f"adapt_{int(fx)}x_psm6"] = ocr_engine._read_candidate(upscale(a, fx), "--oem 3 --psm 6")
    # adaptive psm 7 (single line)
    out["adapt_psm7"] = ocr_engine._read_candidate(upscale(a, 3.0), "--oem 3 --psm 7")
    out["gray_3x_psm7"] = ocr_engine._read_candidate(upscale(gray, 3.0), "--oem 3 --psm 7")
    out["otsu_3x_psm7"] = ocr_engine._read_candidate(upscale(o, 3.0), "--oem 3 --psm 7")
    # denoised grayscale
    try:
        dn = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        out["denoise_3x_psm6"] = ocr_engine._read_candidate(upscale(dn, 3.0), "--oem 3 --psm 6")
        out["denoise_otsu_3x_psm6"] = ocr_engine._read_candidate(upscale(otsu(dn), 3.0), "--oem 3 --psm 6")
    except Exception as e:
        out["denoise_error"] = (str(e), -1)
    return out


def main():
    ocr_engine.init_tesseract()
    img = build_synthetic_factorial_image()
    norm = cv_engine.normalize_image(img)
    blocks, _ = cv_engine.detect_symbols(norm)

    for bid in (3, 4, 5, 6, 8, 9):
        b = next(x for x in blocks if x["id"] == bid)
        x, y, bw, bh = b["bbox"]
        pad = max(6, int(round(min(bw, bh) * 0.12)))
        x1, y1 = max(0, x - pad), max(0, y - pad)
        x2, y2 = min(norm.shape[1], x + bw + pad), min(norm.shape[0], y + bh + pad)
        roi = norm[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        print(f"\n=== BLOCK #{bid} type={b['type']} ===")
        for name, (txt, conf) in variants(gray).items():
            print(f"   {name:<22} conf={conf:6.1f}  text={txt!r}")


if __name__ == "__main__":
    main()
