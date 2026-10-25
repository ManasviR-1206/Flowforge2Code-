import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
from tests.test_stage2_image_upload import build_synthetic_factorial_image
import cv_engine

bgr = build_synthetic_factorial_image()
h, w = bgr.shape[:2]
params = cv_engine.get_adaptive_params(h, w)
blocks, thresh = cv_engine.detect_symbols(bgr)

mask = thresh.copy()
pad = params["pad"]
for block in blocks:
    bx, by, bw, bh = block["bbox"]
    cv2.rectangle(mask, (max(0, bx - pad), max(0, by - pad)), (min(w, bx + bw + pad), min(h, by + bh + pad)), 0, -1)

route_mask = cv2.morphologyEx(
    mask,
    cv2.MORPH_CLOSE,
    cv2.getStructuringElement(cv2.MORPH_RECT, params["k_morph"]),
)
component_count, component_labels, component_stats, _ = cv2.connectedComponentsWithStats(
    (route_mask > 0).astype(np.uint8), 8
)

def endpoint_ink(px: int, py: int) -> int:
    radius = params["endpoint_radius"]
    crop = thresh[max(0, py - radius):min(h, py + radius + 1), max(0, px - radius):min(w, px + radius + 1)]
    return int(np.count_nonzero(crop))

for component_id in range(1, component_count):
    component_x, component_y, component_w, component_h, area = component_stats[component_id]
    if area < params["min_component_area"]:
        continue
    component = component_labels[
        component_y:component_y + component_h,
        component_x:component_x + component_w,
    ] == component_id
    local_ys, local_xs = np.where(component)
    xs = local_xs + component_x
    ys = local_ys + component_y

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
                "block": block,
                "point": (ex, ey),
                "dist": distance,
                "ink": ink,
            })
    if len(endpoints) == 2:
        ep1, ep2 = endpoints[0], endpoints[1]
        if {ep1['block']['id'], ep2['block']['id']} == {9, 5}:
            print(f"Synthetic 9<->5: ep1 (block {ep1['block']['id']}) ink={ep1['ink']}, ep2 (block {ep2['block']['id']}) ink={ep2['ink']}")
            diff = abs(ep1['ink'] - ep2['ink'])
            print(f"diff={diff}, ink_diff_thresh={params['ink_diff_thresh']}")
