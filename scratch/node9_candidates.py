import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))
import cv2
import cv_engine
import ocr_engine
import api_server
import test_stage2_image_upload as t

image = t.build_synthetic_factorial_image()
img = cv_engine.normalize_image(image)
h, w = img.shape[:2]
blocks, _ = cv_engine.detect_symbols(img)
for b in blocks:
    x, y, bw, bh = b["bbox"]
    text, conf = ocr_engine.extract_block_text_with_confidence(img, b["bbox"])
    if "i +" in text or "i+" in text:
        print("block", b["id"], b["type"], b["bbox"], "->", repr(text), conf)
