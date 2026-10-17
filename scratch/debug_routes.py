import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
from PIL import Image
import cv_engine

img_path = r"C:\Users\Manasvi R\Downloads\Factorial Flowchart_ Input, Loop, Output.png"
pil_img = Image.open(img_path).convert("RGB")
img = cv_engine.normalize_image(pil_img)
blocks, thresh = cv_engine.detect_symbols(img)

# Let's inspect HoughLines and ConnectedComponents in cv_engine
h, w = thresh.shape[:2]
params = cv_engine.get_adaptive_params(h, w)
print("Params:", params)

# Let's trace detect_connections manually
mask = thresh.copy()
pad = params["pad"]
for block in blocks:
    bx, by, bw, bh = block["bbox"]
    cv2.rectangle(mask, (max(0, bx - pad), max(0, by - pad)), (min(w, bx + bw + pad), min(h, by + bh + pad)), 0, -1)

lines = cv2.HoughLinesP(
    mask, 1, np.pi / 180,
    threshold=params["hough_thresh"],
    minLineLength=params["min_line_len"],
    maxLineGap=params["max_line_gap"]
)
print("Hough lines count:", len(lines) if lines is not None else 0)

# Check route_mask and connected components
route_mask = cv2.morphologyEx(
    mask,
    cv2.MORPH_CLOSE,
    cv2.getStructuringElement(cv2.MORPH_RECT, params["k_morph"]),
)
component_count, component_labels, component_stats, _ = cv2.connectedComponentsWithStats(
    (route_mask > 0).astype(np.uint8), 8
)
print("Component count:", component_count)

def endpoint_ink(px: int, py: int) -> int:
    radius = params["endpoint_radius"]
    crop = thresh[max(0, py - radius):min(h, py + radius + 1), max(0, px - radius):min(w, px + radius + 1)]
    return int(np.count_nonzero(crop))

for comp_id in range(1, component_count):
    cx, cy, cw, ch, area = component_stats[comp_id]
    if area < params["min_component_area"]:
        continue
    component = component_labels[cy:cy+ch, cx:cx+cw] == comp_id
    local_ys, local_xs = np.where(component)
    xs = local_xs + cx
    ys = local_ys + cy

    endpoints = []
    for block in blocks:
        bx, by, bw, bh = block["bbox"]
        dx = np.maximum(np.maximum(bx - xs, 0), xs - (bx + bw))
        dy = np.maximum(np.maximum(by - ys, 0), ys - (by + bh))
        distances = np.hypot(dx, dy)
        index = int(np.argmin(distances))
        distance = float(distances[index])
        if distance <= params["route_dist"]:
            ex, ey = int(xs[index]), int(ys[index])
            ink = endpoint_ink(ex, ey)
            endpoints.append({
                "block_id": block["id"],
                "point": (ex, ey),
                "dist": distance,
                "ink": ink,
            })
    if len(endpoints) >= 2:
        print(f"Comp {comp_id} (area={area}, box=({cx},{cy},{cw},{ch})):")
        for ep in endpoints:
            print(f"  Endpoint block {ep['block_id']}, pt={ep['point']}, dist={ep['dist']:.1f}, ink={ep['ink']}")
