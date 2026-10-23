import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
from PIL import Image
import cv_engine
import ocr_engine
from scratch.test_full_block_ocr import read_candidate_lines, clean_text_advanced

img_path = r"C:\Users\Manasvi R\Downloads\Factorial Flowchart_ Input, Loop, Output.png"
pil_img = Image.open(img_path).convert("RGB")
img = cv_engine.normalize_image(pil_img)
blocks, thresh = cv_engine.detect_symbols(img)

for b in blocks:
    x, y, w, h = b["bbox"]
    crop = img[y:y+h, x:x+w]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    
    # 1. raw gray
    t1, c1 = read_candidate_lines(gray, "--oem 3 --psm 6")
    # 2. raw gray psm 11
    t2, c2 = read_candidate_lines(gray, "--oem 3 --psm 11")
    # 3. inner
    ih, iw = crop.shape[:2]
    inner = gray[int(ih*0.15):int(ih*0.85), int(iw*0.12):int(iw*0.88)]
    t3, c3 = read_candidate_lines(inner, "--oem 3 --psm 6") if inner.size else ("", -1)
    # 4. inner psm 11
    t4, c4 = read_candidate_lines(inner, "--oem 3 --psm 11") if inner.size else ("", -1)
    
    print(f"\n--- Block {b['id']} ({b['type']}) ---")
    print(f"  raw gray psm 6:  {repr(clean_text_advanced(t1))} (conf={c1:.1f})")
    print(f"  raw gray psm 11: {repr(clean_text_advanced(t2))} (conf={c2:.1f})")
    print(f"  inner psm 6:     {repr(clean_text_advanced(t3))} (conf={c3:.1f})")
    print(f"  inner psm 11:    {repr(clean_text_advanced(t4))} (conf={c4:.1f})")
