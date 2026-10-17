import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2, numpy as np
import cv_engine, ocr_engine, api_server

IMG = r"C:\Users\Manasvi R\Downloads\Largest of Three Numbers Flowchart.png"
with open(IMG, "rb") as f:
    raw = f.read()
img = cv_engine.normalize_image(api_server.pil_from_upload(raw))
blocks, thresh = cv_engine.detect_symbols(img)

# Capture candidate lists for decision blocks
calls = []
_orig = ocr_engine.select_best_candidate
def spy(cands):
    res = _orig(cands)
    calls.append((list(cands), res))
    return res
ocr_engine.select_best_candidate = spy

for b in blocks:
    b["text"], b["text_confidence"] = ocr_engine.extract_block_text_with_confidence(img, b["bbox"])

# calls order == blocks order
for b, (cands, res) in zip(blocks, calls):
    if b["type"] != "decision":
        continue
    print(f"\n===== decision block {b['id']} bbox={b['bbox']} -> winner={res[0]!r} conf={res[1]}")
    for t, c in cands:
        key = ocr_engine._norm_reading_key(t)
        print(f"   cand {t!r:50} conf={c:7.2f} key={key!r:30} rank={ocr_engine._candidate_rank((t,c)):7.1f}")

    # Box-level view of the ROI
    x, y, w, h = b["bbox"]
    pad = 4
    roi = img[max(0,y-pad):y+h+pad, max(0,x-pad):x+w+pad]
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gs = cv2.resize(g, (0,0), fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    boxes = ocr_engine.pytesseract.image_to_boxes(gs).strip()
    H, W = gs.shape[:2]
    print(f"   -- image_to_boxes ({len(boxes.splitlines())} glyphs) --")
    for line in boxes.splitlines():
        p = line.split()
        if len(p) < 5:
            continue
        ch, l, bt, r, tt = p[0], int(p[1]), int(p[2]), int(p[3]), int(p[4])
        if ch in "<>=2z!_":
            top = H - tt; bot = H - bt
            ch_w = max(1, r - l); ch_h = max(1, bot - top)
            strip = gs[max(top, bot - max(2,int(ch_h*0.28))):bot, max(0,l-2):min(W,r+2)]
            frac = 0.0
            if strip.size:
                _, bink = cv2.threshold(strip, 180, 255, cv2.THRESH_BINARY_INV)
                rows = np.sum(bink > 0, axis=1)
                frac = round(float(max(rows))/ch_w, 2) if ch_w else 0.0
            print(f"      {ch!r} l={l} r={r} top={top} bot={bot} underline_frac={frac}")
