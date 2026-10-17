import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import cv_engine, ocr_engine, api_server, logic_engine

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
    text, conf = ocr_engine.extract_block_text_with_confidence(img, b["bbox"])
    cons = ocr_engine.comparison_operators(text)
    sigs = ocr_engine.read_condition_operator_signatures(roi)
    matching = [s for s in sigs if len(s) == len(cons)]
    rep = ocr_engine.recover_condition_operators(text, roi)
    print(f"\n=== dec {b['id']} bbox={b['bbox']} conf={conf}")
    print(f"    text    = {text!r}")
    print(f"    cons    = {cons}   valid={api_server._decision_condition_is_valid(text)}")
    print(f"    sigs    = {sigs}")
    print(f"    matching= {matching}")
    print(f"    repaired= {rep!r}  changed={rep != text} valid={api_server._decision_condition_is_valid(rep)}")
