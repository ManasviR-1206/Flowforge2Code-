import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
from PIL import Image
import cv_engine
import ocr_engine

img_path = r"C:\Users\Manasvi R\Downloads\Factorial Flowchart_ Input, Loop, Output.png"
pil_img = Image.open(img_path).convert("RGB")
img = cv_engine.normalize_image(pil_img)
blocks, thresh = cv_engine.detect_symbols(img)
connections, warnings = cv_engine.detect_connections(thresh, blocks)

# Decision block
b4 = next(b for b in blocks if b["type"] == "decision")
bx, by, bw, bh = b4["bbox"]
dcx, dcy = b4["center"]
h_img, w_img = img.shape[:2]

pad_x, pad_y = 160, 100
crop_x1 = max(0, bx - pad_x)
crop_y1 = max(0, by - pad_y)
crop_x2 = min(w_img, bx + bw + pad_x)
crop_y2 = min(h_img, by + bh + pad_y)

surround = img[crop_y1:crop_y2, crop_x1:crop_x2]
data = ocr_engine.pytesseract.image_to_data(
    surround, config="--psm 11", output_type=ocr_engine.pytesseract.Output.DICT
)

detected_labels = []
for i in range(len(data["text"])):
    t = data["text"][i].strip()
    if not t:
        continue
    lbl = ocr_engine.clean_branch_label(t)
    if lbl:
        abs_x = crop_x1 + data["left"][i] + data["width"][i] // 2
        abs_y = crop_y1 + data["top"][i] + data["height"][i] // 2
        conf = float(data["conf"][i])
        detected_labels.append({"label": lbl, "pos": (abs_x, abs_y), "conf": conf})

print("Detected branch labels around decision:", detected_labels)

# Match each detected branch label to the closest outgoing connection from decision
dec_conns = [c for c in connections if c["from"] == b4["id"]]
blocks_by_id = {b["id"]: b for b in blocks}

for dl in detected_labels:
    lbl = dl["label"]
    lx, ly = dl["pos"]
    # Find which outgoing connection is closest
    best_c = None
    min_dist = float("inf")
    for c in dec_conns:
        target_b = blocks_by_id[c["to"]]
        tcx, tcy = target_b["center"]
        # Distance to vector or target direction
        # If label is left of decision (lx < dcx) and target is left (tcx < dcx):
        same_side = (lx < dcx and tcx < dcx) or (lx > dcx and tcx > dcx) or (ly > dcy and tcy > dcy)
        if same_side:
            best_c = c
            break
    if best_c:
        best_c["branch"] = lbl
        print(f"Assigned branch '{lbl}' to connection {best_c['from']} -> {best_c['to']}")

for c in dec_conns:
    print(f"Final conn {c['from']} -> {c['to']}: branch={repr(c.get('branch'))}")
