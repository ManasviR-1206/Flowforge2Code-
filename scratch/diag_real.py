import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
from PIL import Image

import cv_engine
import ocr_engine
import api_server

img_path = sys.argv[1]
print("File exists:", os.path.exists(img_path))

with open(img_path, "rb") as f:
    raw_bytes = f.read()

pil_img = api_server.pil_from_upload(raw_bytes)
img = cv_engine.normalize_image(pil_img)
print(f"Normalized image shape: {img.shape}")

blocks, thresh = cv_engine.detect_symbols(img)
print(f"Detected {len(blocks)} blocks:")
for b in blocks:
    text, conf = ocr_engine.extract_block_text_with_confidence(img, b["bbox"])
    b["text"] = text
    b["text_confidence"] = conf
    b["text_uncertain"] = (not text or conf < api_server.OCR_REVIEW_CONFIDENCE)
    print(f"  Block {b['id']}: type={b['type']}, bbox={b['bbox']}, center={b['center']}, conf={conf:.1f}, uncertain={b['text_uncertain']}, text={text!r}")

connections, warnings = cv_engine.detect_connections(thresh, blocks)
print(f"Detected {len(connections)} connections:")
for c in connections:
    print(f"  Connection: {c['from']} -> {c['to']}, conf={c['confidence']}, uncertain={c.get('uncertain')}, branch={c.get('branch')!r}")

# Replicate branch-label OCR (surround scan) from api_server
if ocr_engine.tesseract_available():
    blocks_by_id = {int(block["id"]): block for block in blocks}
    h, w = img.shape[:2]
    for block in blocks:
        if block.get("type") != "decision":
            continue
        bx, by, bw, bh = block["bbox"]
        dcx, dcy = block["center"]
        pad_x, pad_y = max(140, int(bw * 0.6)), max(90, int(bh * 0.5))
        c_x1 = max(0, bx - pad_x)
        c_y1 = max(0, by - pad_y)
        c_x2 = min(w, bx + bw + pad_x)
        c_y2 = min(h, by + bh + pad_y)
        surround_crop = img[c_y1:c_y2, c_x1:c_x2]
        s_data = ocr_engine.pytesseract.image_to_data(
            surround_crop, config="--psm 11", output_type=ocr_engine.pytesseract.Output.DICT
        )
        texts = s_data.get("text", [])
        confs = s_data.get("conf", [])
        print(f"Surround OCR for decision {block['id']}:")
        for i in range(len(texts)):
            if str(texts[i]).strip():
                print(f"    {texts[i]!r} conf={confs[i]}")

react_nodes = api_server.blocks_to_react_nodes(blocks, img_height=h, img_width=w, connections=connections)
react_edges = api_server.connections_to_react_edges(connections)
print("React nodes:")
for n in react_nodes:
    print(f"  {n['id']}: type={n['type']} label={n['data']['label']!r} needs_review={n['data']['needs_review']}")
print("React edges:")
for e in react_edges:
    print(f"  {e['source']} -> {e['target']} label={e['label']!r} uncertain={e['data']['uncertain']}")
print("Warnings:", warnings)
