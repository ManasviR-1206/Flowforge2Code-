import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2, numpy as np
import cv_engine, ocr_engine, api_server
import pytesseract

OP_RE = re.compile(r"<=|>=|==|!=|[<>]|=")
IMG = r"C:\Users\Manasvi R\Downloads\Largest of Three Numbers Flowchart.png"
with open(IMG, "rb") as f:
    raw = f.read()
img = cv_engine.normalize_image(api_server.pil_from_upload(raw))
blocks, _ = cv_engine.detect_symbols(img)

def upgrade(crop, text):
    g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    txt = text.replace("=>", ">=").replace("=<", "<=")
    try:
        for line in pytesseract.image_to_boxes(g).splitlines():
            p = line.split()
            if len(p) >= 5 and p[0] in "<>":
                if ocr_engine.check_underline_under_operator(g, (p[0], int(p[1]), int(p[2]), int(p[3]), int(p[4]))):
                    txt = txt.replace("<", "<=").replace(">", ">=")
                    break
    except Exception:
        pass
    return txt

results = []
for b in blocks:
    if b["type"] != "decision":
        continue
    x, y, w, h = b["bbox"]
    for inset in [round(0.10 + 0.02*i, 2) for i in range(16)]:
        x1, x2 = x + int(w*inset), x + int(w*(1-inset))
        y1, y2 = y + int(h*inset), y + int(h*(1-inset))
        c = cv2.cvtColor(img[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
        if c.size == 0:
            continue
        for fx in (2, 3, 4):
            up = cv2.resize(c, (0,0), fx=fx, fy=fx, interpolation=cv2.INTER_CUBIC)
            preps = {
                "gray": up,
                "otsu": cv2.threshold(up, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1],
                "adap": cv2.adaptiveThreshold(up, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10),
            }
            for pname, prep in preps.items():
                for psm in (6, 4):
                    try:
                        txt = pytesseract.image_to_string(prep, config=f"--oem 3 --psm {psm}")
                    except Exception:
                        continue
                    up2 = upgrade(prep, txt)
                    ops = OP_RE.findall(up2)
                    if len(ops) >= 2 and re.search(r"[A-Za-z]", up2):
                        results.append((b["id"], inset, fx, pname, psm, ops, up2.replace("\n", "\\n")))

for r in sorted(results):
    print(f"dec{r[0]} inset={r[1]} {r[2]}x {r[3]:4} psm{r[4]} ops={r[5]}  {r[6]!r}")
print("total", len(results))
