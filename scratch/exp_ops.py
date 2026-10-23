import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2, numpy as np
import cv_engine, ocr_engine, api_server
import pytesseract

IMG = r"C:\Users\Manasvi R\Downloads\Largest of Three Numbers Flowchart.png"
with open(IMG, "rb") as f:
    raw = f.read()
img = cv_engine.normalize_image(api_server.pil_from_upload(raw))
blocks, thresh = cv_engine.detect_symbols(img)

WL = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 <>=?!+-*/%()_:;,._'\""

def variants(roi):
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    out = {}
    out["gray_2x_psm6"] = (cv2.resize(g,(0,0),fx=2,fy=2,interpolation=cv2.INTER_CUBIC), "--oem 3 --psm 6")
    out["gray_3x_psm6"] = (cv2.resize(g,(0,0),fx=3,fy=3,interpolation=cv2.INTER_CUBIC), "--oem 3 --psm 6")
    _, ot = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    out["otsu_2x_psm6"] = (cv2.resize(ot,(0,0),fx=2,fy=2,interpolation=cv2.INTER_CUBIC), "--oem 3 --psm 6")
    out["otsu_2x_psm6_wl"] = (cv2.resize(ot,(0,0),fx=2,fy=2,interpolation=cv2.INTER_CUBIC), "--oem 3 --psm 6 -c tessedit_char_whitelist=" + WL)
    out["otsu_3x_psm6_wl"] = (cv2.resize(ot,(0,0),fx=3,fy=3,interpolation=cv2.INTER_CUBIC), "--oem 3 --psm 6 -c tessedit_char_whitelist=" + WL)
    ad = cv2.adaptiveThreshold(g,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,11,2)
    out["adap_2x_psm6"] = (cv2.resize(ad,(0,0),fx=2,fy=2,interpolation=cv2.INTER_CUBIC), "--oem 3 --psm 6")
    # remove long horizontal strokes (the >= underline / = bars) then OCR to expose base chevron
    bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    horiz = cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT,(max(8,int(g.shape[1]*0.05)),1)))
    nobar = cv2.subtract(bw, horiz)
    nobar_img = cv2.bitwise_not(nobar)
    out["nobar_2x_psm6_wl"] = (cv2.resize(nobar_img,(0,0),fx=2,fy=2,interpolation=cv2.INTER_CUBIC), "--oem 3 --psm 6 -c tessedit_char_whitelist=" + WL)
    out["nobar_3x_psm6"] = (cv2.resize(nobar_img,(0,0),fx=3,fy=3,interpolation=cv2.INTER_CUBIC), "--oem 3 --psm 6")
    return out

for b in blocks:
    if b["type"] != "decision":
        continue
    x,y,w,h = b["bbox"]
    for tag, (cx1,cx2,cy1,cy2) in (
        ("tight", (x+int(w*0.18), x+int(w*0.82), y+int(h*0.18), y+int(h*0.82))),
        ("mid",   (x+int(w*0.25), x+int(w*0.75), y+int(h*0.25), y+int(h*0.75))),
    ):
        roi = img[cy1:cy2, cx1:cx2]
        if roi.size == 0:
            continue
        print(f"\n##### decision {b['id']} {tag} roi={roi.shape}")
        for name, (im, cfg) in variants(roi).items():
            try:
                txt = pytesseract.image_to_string(im, config=cfg).replace("\n","\\n").strip()
            except Exception as e:
                txt = f"ERR {e}"
            print(f"   {name:20} -> {txt!r}")
