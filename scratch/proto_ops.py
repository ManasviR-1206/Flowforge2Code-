import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2, numpy as np
import cv_engine, ocr_engine, api_server
import pytesseract

OP_RE = re.compile(r"<=|>=|==|!=|[<>]|=")

def ops(text):
    return OP_RE.findall(text)

def upgrade(crop, text):
    g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    has = False
    try:
        for line in pytesseract.image_to_boxes(g).splitlines():
            p = line.split()
            if len(p) >= 5 and p[0] in "<>":
                if ocr_engine.check_underline_under_operator(g, (p[0], int(p[1]), int(p[2]), int(p[3]), int(p[4]))):
                    has = True
                    break
    except Exception:
        pass
    return text.replace("<", "<=").replace(">", ">=") if has else text

def read_ops(roi):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    best = ""
    for inset in (0.16, 0.22, 0.28, 0.34):
        y1, y2 = int(h * inset), int(h * (1 - inset))
        x1, x2 = int(w * inset), int(w * (1 - inset))
        c = gray[y1:y2, x1:x2]
        if c.size == 0:
            continue
        preps = [cv2.resize(c, (0, 0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC)]
        preps.append(cv2.resize(cv2.threshold(c, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1], (0, 0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
        for prep in preps:
            try:
                txt = pytesseract.image_to_string(prep, config="--oem 3 --psm 6")
            except Exception:
                continue
            up = upgrade(prep, txt)
            if len(ops(up)) > len(ops(best)):
                best = up
    return ops(best), best

for path, name in ((r"C:\Users\Manasvi R\Downloads\Largest of Three Numbers Flowchart.png", "largest"),
                   (r"C:\Users\Manasvi R\Downloads\Even or Odd Flowchart.png", "oddeven")):
    with open(path, "rb") as f:
        raw = f.read()
    img = cv_engine.normalize_image(api_server.pil_from_upload(raw))
    blocks, _ = cv_engine.detect_symbols(img)
    print(f"\n######## {name}")
    for b in blocks:
        if b["type"] != "decision":
            continue
        x, y, w, h = b["bbox"]
        roi = img[y:y+h, x:x+w]
        seq, best = read_ops(roi)
        # consensus text from main path
        cons = ocr_engine.extract_block_text_with_confidence(img, b["bbox"])[0]
        print(f"  dec {b['id']} consensus={cons!r} ops={ops(cons)}")
        print(f"        pixel_best={best!r} ops={seq}")
