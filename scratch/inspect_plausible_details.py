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
    print(f"\n================ Block {bid} ================")
    x, y, w, h = b["bbox"]
    img_h, img_w = img.shape[:2]

    pad = max(6, int(round(min(w, h) * 0.12)))
    x1, y1 = max(0, x - pad), max(0, y - pad)
    x2, y2 = min(img_w, x + w + pad), min(img_h, y + h + pad)

    roi = img[y1:y2, x1:x2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    candidates = []
    full_size = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    candidates.append(ocr_engine._read_candidate(full_size, "--oem 3 --psm 6"))
    candidates.append(ocr_engine._read_candidate_string(full_size, "--oem 3 --psm 6"))
    candidates.append(ocr_engine._read_candidate(full_size, "--oem 3 --psm 4"))

    height, width = gray.shape[:2]
    inner = gray[int(height * 0.2):int(height * 0.8), int(width * 0.16):int(width * 0.84)]
    if inner.size:
        inner_size = cv2.resize(inner, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        candidates.append(ocr_engine._read_candidate(inner_size, "--oem 3 --psm 6"))
        candidates.append(ocr_engine._read_candidate_string(inner_size, "--oem 3 --psm 6"))

    adaptive = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    adaptive_size = cv2.resize(
        adaptive, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC
    )
    candidates.append(ocr_engine._read_candidate(adaptive_size, "--oem 3 --psm 11"))
    candidates.append(ocr_engine._read_candidate(adaptive_size, "--oem 3 --psm 12"))

    shape_x1 = min(img_w, x + int(w * 0.12))
    shape_y1 = min(img_h, y + int(h * 0.2))
    shape_x2 = max(shape_x1, min(img_w, x + int(w * 0.88)))
    shape_y2 = max(shape_y1, min(img_h, y + int(h * 0.8)))
    shape_inner = img[shape_y1:shape_y2, shape_x1:shape_x2]
    if shape_inner.size:
        shape_gray = cv2.cvtColor(shape_inner, cv2.COLOR_BGR2GRAY)
        shape_gray_size = cv2.resize(
            shape_gray, (0, 0), fx=3.0, fy=3.0,
            interpolation=cv2.INTER_CUBIC,
        )
        candidates.append(ocr_engine._read_candidate(shape_gray_size, "--oem 3 --psm 6"))
        candidates.append(ocr_engine._read_candidate_string(shape_gray_size, "--oem 3 --psm 6"))
        if min(shape_gray.shape[:2]) >= 11:
            shape_adaptive = cv2.adaptiveThreshold(
                shape_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2,
            )
            shape_size = cv2.resize(
                shape_adaptive, (0, 0), fx=3.0, fy=3.0,
                interpolation=cv2.INTER_CUBIC,
            )
            candidates.append(ocr_engine._read_candidate(shape_size, "--oem 3 --psm 11"))
            candidates.append(ocr_engine._read_candidate(shape_size, "--oem 3 --psm 12"))

    exact_box = img[y:y+h, x:x+w]
    if exact_box.size:
        exact_gray = cv2.cvtColor(exact_box, cv2.COLOR_BGR2GRAY)
        candidates.append(ocr_engine._read_candidate(exact_gray, "--oem 3 --psm 6"))
        candidates.append(ocr_engine._read_candidate_string(exact_gray, "--oem 3 --psm 6"))
        candidates.append(ocr_engine._read_candidate(exact_gray, "--oem 3 --psm 11"))

    plausible_candidates = set()
    for c_text, c_conf in candidates:
        cand_clean = ocr_engine.clean_ocr_text(c_text)
        if c_conf < 30 or re.search(r"[^A-Za-z0-9_+\-*/%=<>?! .\n]", cand_clean):
            continue
        if not re.search(r"\b[A-Za-z_]\w*\s*=", cand_clean) and not re.search(
            r"(?:<=|>=|==|!=|[<>])", cand_clean
        ) and not re.search(r"\b(?:input|print|start|end)\b", cand_clean, re.I):
            continue
        norm = re.sub(r"[^a-z0-9_+\-*/%=<>?!]", "", cand_clean.lower())
        plausible_candidates.add((norm, cand_clean, c_conf))
    print("Plausible candidates:")
    for p in plausible_candidates:
        print("  ", p)
