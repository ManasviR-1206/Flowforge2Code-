import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import cv_engine, ocr_engine, api_server
import pytesseract

IMG = r"C:\Users\Manasvi R\Downloads\Largest of Three Numbers Flowchart.png"
with open(IMG, "rb") as f:
    raw = f.read()
img = cv_engine.normalize_image(api_server.pil_from_upload(raw))
blocks, _ = cv_engine.detect_symbols(img)

for b in blocks:
    if b["type"] != "decision":
        continue
    x, y, w, h = b["bbox"]
    roi = img[y:y + h, x:x + w]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    H, W = gray.shape[:2]
    text, conf = ocr_engine.extract_block_text_with_confidence(img, b["bbox"])
    cons = ocr_engine.comparison_operators(text)
    print(f"\n===== dec {b['id']} cons={cons} text={text!r} shape={gray.shape}")
    for inset in (0.14, 0.16, 0.18, 0.20, 0.22, 0.24, 0.26, 0.28, 0.30, 0.32):
        y1, y2 = int(H * inset), int(H * (1 - inset))
        x1, x2 = int(W * inset), int(W * (1 - inset))
        crop = gray[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
        if crop.size == 0:
            continue
        _, otsu = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        adap = cv2.adaptiveThreshold(crop, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10)
        for fx in (2, 3):
            for pname, base in (("gray", crop), ("otsu", otsu), ("adap", adap)):
                prep = cv2.resize(base, (0, 0), fx=fx, fy=fx, interpolation=cv2.INTER_CUBIC)
                try:
                    t = pytesseract.image_to_string(prep, config="--oem 3 --psm 6")
                except Exception as e:
                    continue
                up = ocr_engine._upgrade_underlined_chevrons(prep, t)
                ops = ocr_engine.comparison_operators(up)
                if len(ops) == len(cons):
                    print(f"  MATCH inset={inset} {fx}x {pname:4} ops={ops} raw={t.strip()!r} up={up.strip()!r}")
