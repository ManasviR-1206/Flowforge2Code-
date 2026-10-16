"""Diagnostic: trace the full upload->graph pipeline on a synthetic factorial image.

Prints OCR candidates/confidence, detected blocks, node->label mapping, and edges.
Synthetic-only; not a real-image validation.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
import cv_engine
import ocr_engine
import logic_engine

from tests.test_stage2_image_upload import build_synthetic_factorial_image


def main():
    ocr_engine.init_tesseract()
    print("tesseract available:", ocr_engine.tesseract_available())

    img = build_synthetic_factorial_image()
    norm = cv_engine.normalize_image(img)
    h, w = norm.shape[:2]
    print("normalized size:", w, "x", h)

    blocks, thresh = cv_engine.detect_symbols(norm)
    print(f"\n=== DETECTED BLOCKS ({len(blocks)}) ===")
    for b in blocks:
        print(f"  #{b['id']:>2} type={b['type']:<14} bbox={b['bbox']} center={b['center']}")

    connections, warnings = cv_engine.detect_connections(thresh, blocks)
    print(f"\n=== CONNECTIONS ({len(connections)}) ===")
    for c in connections:
        print(f"  {c['from']} -> {c['to']}  branch={c.get('branch')!r} conf={c['confidence']} uncertain={c.get('uncertain')}")
    print("\n=== CONNECTION WARNINGS ===")
    for wmsg in warnings:
        print("  -", wmsg)

    print("\n=== PER-BLOCK OCR (all candidates) ===")
    for b in blocks:
        x, y, bw, bh = b["bbox"]
        pad = max(6, int(round(min(bw, bh) * 0.12)))
        x1, y1 = max(0, x - pad), max(0, y - pad)
        x2, y2 = min(w, x + bw + pad), min(h, y + bh + pad)
        roi = norm[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        full = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        txt, conf = ocr_engine._read_candidate(full, "--oem 3 --psm 6")
        text, text_conf = ocr_engine.extract_block_text_with_confidence(norm, b["bbox"])
        print(f"  #{b['id']:>2} raw_psm6={txt!r} (conf={conf:.1f})  ->  final={text!r} (conf={text_conf:.1f})")

    # Clean-text destructive check
    print("\n=== clean_ocr_text BEHAVIOR (destructive?) ===")
    for probe in [
        "fact = fact * i",
        "i = i + 1",
        "i <= n?",
        "fact = 1",
        "Input n",
        "Print fact",
        "i < n?",
        "n % 2 == 0?",
    ]:
        print(f"  {probe!r} -> {ocr_engine.clean_ocr_text(probe)!r}")


if __name__ == "__main__":
    main()
