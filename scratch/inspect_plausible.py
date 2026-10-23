import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2, re
from PIL import Image
import cv_engine
import ocr_engine

img_path = r"C:\Users\Manasvi R\Downloads\Factorial Flowchart_ Input, Loop, Output.png"
pil_img = Image.open(img_path).convert("RGB")
img = cv_engine.normalize_image(pil_img)
blocks, thresh = cv_engine.detect_symbols(img)

for bid in (2, 3, 5):
    b = next(x for x in blocks if x["id"] == bid)
    print(f"\n--- Block {bid} ---")
    x, y, w, h = b["bbox"]
    # We can inspect extract_block_text_with_confidence step by step
    text, conf = ocr_engine.extract_block_text_with_confidence(img, b["bbox"])
    print(f"Result: {repr(text)}, conf={conf}")
