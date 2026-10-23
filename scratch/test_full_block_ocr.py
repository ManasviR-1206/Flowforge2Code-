import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import re
import numpy as np
from PIL import Image
import cv_engine
import ocr_engine

def check_underline_under_operator(roi, box_tuple):
    if len(roi.shape) == 3:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    else:
        gray = roi
    h, w = gray.shape[:2]
    char, l, b_tess, r, t_tess = box_tuple
    top = h - t_tess
    bot = h - b_tess
    char_h = bot - top
    char_w = r - l
    check_y1 = bot
    check_y2 = min(h, bot + int(char_h * 0.9) + 6)
    check_x1 = max(0, l - 3)
    check_x2 = min(w, r + 3)
    below_crop = gray[check_y1:check_y2, check_x1:check_x2]
    if below_crop.size == 0:
        return False
    _, bin_below = cv2.threshold(below_crop, 180, 255, cv2.THRESH_BINARY_INV)
    row_ink = np.sum(bin_below > 0, axis=1)
    return any(cnt >= char_w * 0.45 for cnt in row_ink)

def read_candidate_lines(image, config="--oem 3 --psm 6"):
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

def clean_text_advanced(raw_text: str) -> str:
    cleaned = raw_text.strip()
    if not cleaned:
        return ""
    # Unicode replacements
    cleaned = cleaned.replace("≤", "<=").replace("≥", ">=").replace("≠", "!=").replace("×", "*")
    # Fix keyword typos
    cleaned = re.sub(r'\b[iI][nN][pP][uU][tT]\b', 'Input', cleaned)
    cleaned = re.sub(r'\b[pP][rR][iI][nN][tT]\b', 'Print', cleaned)
    cleaned = re.sub(r'\b[sS][tT][aA][rR][tT]\b', 'Start', cleaned)
    cleaned = re.sub(r'\b[eE][nN][dD]\b', 'End', cleaned)
    # Remove leading noise
    cleaned = re.sub(r'^[:;.,|/\\~`_jJ!?-]+\s+(?=(?:Input|Print|Start|End|[A-Za-z_]\w*\s*=))', '', cleaned)
    cleaned = re.sub(r'^[(\[{]\s*(?=(?:Input|Print|Start|End|[A-Za-z_]\w*\s*=))', '', cleaned, flags=re.I)
    cleaned = re.sub(r'\s+[*+~`]+$', '', cleaned)
    # Math operator normalization
    cleaned = re.sub(r'(\w)\s*=\s*(\w)\s*t\+\s*', r'\1 = \2 + ', cleaned)
    cleaned = re.sub(r'\bt\+\b', '+', cleaned)
    cleaned = re.sub(r'(?<=\w)\s+[xX]\s+(?=\w)', ' * ', cleaned)
    cleaned = re.sub(r'(\w)\s*([+\-*/%]|<=|>=|==|!=|<|>)\s*(\w)', r'\1 \2 \3', cleaned)
    cleaned = re.sub(r'(\w)\s*=\s*(\w)', r'\1 = \2', cleaned)
    # If Input/Print followed by newline and variable: join to single line
    cleaned = re.sub(r'^(Input|Print)\s*\n\s*(\w+)', r'\1 \2', cleaned, flags=re.I)
    # If multiple assignments on one line, split into separate lines
    pattern = r'(\b\d+|\b[A-Za-z_]\w*)\s+([A-Za-z_]\w*\s*(?:=|\+=|-=|\*=|/=|%=)(?!=))'
    prev = None
    while prev != cleaned:
        prev = cleaned
        cleaned = re.sub(pattern, r'\1\n\2', cleaned)
    return cleaned.strip()

img_path = r"C:\Users\Manasvi R\Downloads\Factorial Flowchart_ Input, Loop, Output.png"
pil_img = Image.open(img_path).convert("RGB")
img = cv_engine.normalize_image(pil_img)
blocks, thresh = cv_engine.detect_symbols(img)

for b in blocks:
    x, y, w, h = b["bbox"]
    crop = img[y:y+h, x:x+w]
    # Check inner for decision diamond
    if b["type"] == "decision":
        ih, iw = crop.shape[:2]
        inner = crop[int(ih*0.25):int(ih*0.75), int(iw*0.2):int(iw*0.8)]
        gray_inner = cv2.cvtColor(inner, cv2.COLOR_BGR2GRAY)
        scaled_inner = cv2.resize(gray_inner, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        raw_t, conf = read_candidate_lines(scaled_inner, "--oem 3 --psm 6")
        # Check underline
        boxes = ocr_engine.pytesseract.image_to_boxes(scaled_inner).strip().splitlines()
        for line in boxes:
            parts = line.split()
            char = parts[0]
            if char in ("<", ">"):
                box = (char, int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]))
                if check_underline_under_operator(scaled_inner, box):
                    raw_t = raw_t.replace("<", "<=").replace(">", ">=")
        cleaned = clean_text_advanced(raw_t)
    else:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        scaled = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        raw_t, conf = read_candidate_lines(scaled, "--oem 3 --psm 6")
        cleaned = clean_text_advanced(raw_t)
    print(f"Block {b['id']} ({b['type']}): conf={conf:.1f}")
    print(f"  Raw: {repr(raw_t)}")
    print(f"  Cleaned: {repr(cleaned)}")
