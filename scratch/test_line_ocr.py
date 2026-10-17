import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
from PIL import Image
import cv_engine
import ocr_engine

def read_candidate_with_lines(image, config="--oem 3 --psm 6"):
    data = ocr_engine.pytesseract.image_to_data(
        image,
        config=config,
        output_type=ocr_engine.pytesseract.Output.DICT,
    )
    lines_dict = {}
    confidences = []
    for i in range(len(data["text"])):
        w = data["text"][i].strip()
        if not w:
            continue
        conf = float(data["conf"][i])
        if conf >= 0:
            confidences.append(conf)
        line_key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines_dict.setdefault(line_key, []).append(w)
    if not lines_dict:
        return "", -1
    line_strings = [" ".join(words) for words in lines_dict.values()]
    text = "\n".join(line_strings)
    confidence = sum(confidences) / len(confidences) if confidences else -1
    return text, confidence

img_path = r"C:\Users\Manasvi R\Downloads\Factorial Flowchart_ Input, Loop, Output.png"
pil_img = Image.open(img_path).convert("RGB")
img = cv_engine.normalize_image(pil_img)
blocks, thresh = cv_engine.detect_symbols(img)

for b in blocks:
    x, y, w, h = b["bbox"]
    crop = img[y:y+h, x:x+w]
    t, c = read_candidate_with_lines(crop, "--oem 3 --psm 6")
    print(f"Block {b['id']} ({b['type']}):\n{repr(t)} (conf={c:.1f})\n")
