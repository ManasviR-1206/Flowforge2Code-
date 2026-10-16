import cv2
import numpy as np
from collections import Counter, defaultdict
from PIL import Image

def normalize_image(image_input, target_max_dim=1280):
    """
    Converts image to BGR numpy array and scales down if larger than target_max_dim.
    """
    if isinstance(image_input, Image.Image):
        img = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
    elif isinstance(image_input, np.ndarray):
        img = image_input.copy()
    else:
        raise ValueError("Unsupported image input type")

    h, w = img.shape[:2]
    scale = target_max_dim / max(h, w)
    
    if scale < 1.0:
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
    return img

def classify_shape(approx, cnt, aspect_ratio, circularity):
    """
    Classifies shape contour into flowchart symbol types.
    """
    num_vertices = len(approx)
    x, y, w, h = cv2.boundingRect(cnt)

    if num_vertices == 3:
        return "offpage"  # triangle / pentagon-like pointer often 3-approx

    if num_vertices == 4:
        pts = approx.reshape(4, 2)
        angles = []
        side_lengths = []
        for i in range(4):
            p1 = pts[i]
            p2 = pts[(i + 1) % 4]
            p3 = pts[(i + 2) % 4]
            side_lengths.append(float(np.linalg.norm(p1 - p2)))
            v1 = p1 - p2
            v2 = p3 - p2
            cosine = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-5)
            angle = np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))
            angles.append(angle)

        by_y = sorted(pts, key=lambda p: p[1])
        top, bottom = by_y[:2], by_y[2:]
        top_level = abs(int(top[0][1]) - int(top[1][1])) <= 0.2 * h
        bottom_level = abs(int(bottom[0][1]) - int(bottom[1][1])) <= 0.2 * h
        top_width = abs(float(top[0][0] - top[1][0]))
        bottom_width = abs(float(bottom[0][0] - bottom[1][0]))
        top_center_x = sum(float(point[0]) for point in top) / 2
        bottom_center_x = sum(float(point[0]) for point in bottom) / 2
        side_skew = abs(top_center_x - bottom_center_x)

        if top_level and bottom_level and min(top_width, bottom_width) < 0.8 * max(top_width, bottom_width):
            return "manual_input"

        if top_level and bottom_level and side_skew > max(3, 0.05 * w):
            return "input_output"
        if max(abs(angle - 90) for angle in angles) <= 15 and 0.2 <= aspect_ratio <= 5.0:
            return "process"
        side_ratio = max(side_lengths) / max(min(side_lengths), 1e-5)
        if side_ratio <= 1.3 and circularity < 0.85:
            return "decision"
        return "input_output"

    if num_vertices == 5:
        return "offpage"

    if num_vertices >= 6:
        if num_vertices >= 7 and circularity > 0.58 and 2.0 <= aspect_ratio <= 3.5:
            return "start_end"
        if circularity > 0.72 and 0.6 <= aspect_ratio <= 1.8:
            return "connector" if min(w, h) < 70 and circularity > 0.85 else "start_end"
        if circularity > 0.65:
            return "start_end"
        if aspect_ratio < 0.85:
            return "database"
        return "document" if aspect_ratio > 1.2 else "process"

    return "unknown"

def detect_symbols(img):
    """
    Detects symbols from a preprocessed image array.
    Returns detected blocks list and thresholded binary image.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Otsu adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )

    # Morphological closing
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    contours, hierarchy = cv2.findContours(closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    blocks = []
    block_id = 1
    
    img_area = img.shape[0] * img.shape[1]
    min_area = max(600, img_area * 0.001)
    max_area = img_area * 0.85

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue

        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        x, y, w, h = cv2.boundingRect(cnt)
        aspect_ratio = float(w) / max(1, h)
        circularity = (4 * np.pi * area) / (peri * peri) if peri > 0 else 0

        shape_type = classify_shape(approx, cnt, aspect_ratio, circularity)

        if shape_type != "unknown":
            blocks.append({
                "id": block_id,
                "type": shape_type,
                "bbox": (x, y, w, h),
                "center": (x + w // 2, y + h // 2),
                "area": area
            })
            block_id += 1

    # Filter nested duplicate bounding boxes
    filtered_blocks = filter_overlapping_blocks(blocks)
    return filtered_blocks, thresh

def filter_overlapping_blocks(blocks):
    """
    Removes duplicate contours while retaining individual symbols inside a
    connected contour formed by arrows touching multiple flowchart shapes.
    """
    blocks = sorted(blocks, key=lambda b: b["area"], reverse=True)
    aggregate_ids = set()

    def contains(outer, inner):
        x, y, w, h = outer["bbox"]
        ix, iy, iw, ih = inner["bbox"]
        return (
            outer is not inner
            and ix >= x and iy >= y
            and ix + iw <= x + w and iy + ih <= y + h
        )

    def significantly_overlaps(outer, inner):
        x, y, w, h = outer["bbox"]
        ix, iy, iw, ih = inner["bbox"]
        overlap_width = max(0, min(x + w, ix + iw) - max(x, ix))
        overlap_height = max(0, min(y + h, iy + ih) - max(y, iy))
        overlap_area = overlap_width * overlap_height
        smaller_area = min(w * h, iw * ih)
        return smaller_area > 0 and overlap_area >= smaller_area * 0.18

    for block in blocks:
        if block["type"] == "offpage" and any(
            candidate is not block
            and candidate["type"] != "offpage"
            and significantly_overlaps(block, candidate)
            for candidate in blocks
        ):
            aggregate_ids.add(id(block))

    for block in blocks:
        _, _, width, height = block["bbox"]
        bbox_area = width * height
        nested = [
            candidate for candidate in blocks
            if (contains(block, candidate) or significantly_overlaps(block, candidate))
            and candidate["area"] < block["area"]
            and candidate["bbox"][2] * candidate["bbox"][3] >= bbox_area * 0.02
            and candidate["area"] >= block["area"] * 0.05
        ]
        distinct = []
        for candidate in nested:
            x, y, w, h = candidate["bbox"]
            separated = all(
                x + w <= ox or ox + ow <= x or y + h <= oy or oy + oh <= y
                for ox, oy, ow, oh in (item["bbox"] for item in distinct)
            )
            if separated:
                distinct.append(candidate)
        has_embedded_symbol = any(
            candidate["bbox"][2] * candidate["bbox"][3] < bbox_area * 0.75
            for candidate in distinct
        )
        if len(distinct) >= 2 or has_embedded_symbol:
            aggregate_ids.add(id(block))

    kept = []
    for b in blocks:
        if id(b) in aggregate_ids:
            continue
        if not any(contains(k, b) for k in kept):
            kept.append(b)

    # Re-assign clean sequential IDs sorted top-to-bottom
    kept = sorted(kept, key=lambda b: (b["bbox"][1], b["bbox"][0]))
    for i, b in enumerate(kept):
        b["id"] = i + 1

    return kept

def is_duplicate_reverse(v1, v2):
    if not v1 or not v2:
        return True
    (p1, p2), (q1, q2) = v1, v2
    d1 = np.hypot(p1[0] - q2[0], p1[1] - q2[1])
    d2 = np.hypot(p2[0] - q1[0], p2[1] - q1[1])
    return d1 < 40 and d2 < 40

def detect_connections(thresh_img, blocks):
    """
    Detects directed line segments and uses connected routes to recover loop-back
    arrows that are split into multiple Hough segments.
    """
    connections = []
    warnings = []
    if len(blocks) < 2:
        return connections, warnings

    # Pad 5 clears symbol boundaries (including thick strokes, curved oval arcs,
    # and diamond corners) so shapes don't bridge into connectors or skew ink scoring.
    mask = thresh_img.copy()
    for block in blocks:
        x, y, w, h = block["bbox"]
        pad = 5
        cv2.rectangle(mask, (max(0, x - pad), max(0, y - pad)), (x + w + pad, y + h + pad), 0, -1)
    lines = cv2.HoughLinesP(mask, 1, np.pi / 180, threshold=20, minLineLength=15, maxLineGap=10)
    votes: dict[tuple[int, int], Counter] = defaultdict(Counter)
    vectors: dict[tuple[int, int], dict[tuple[int, int], tuple]] = defaultdict(dict)
    unresolved_pairs = set()
    seen_segments = set()

    def endpoint_ink(x: int, y: int) -> int:
        radius = 8
        crop = mask[max(0, y - radius):y + radius + 1, max(0, x - radius):x + radius + 1]
        return int(np.count_nonzero(crop))

    if lines is not None:
        for x1, y1, x2, y2 in np.asarray(lines).reshape(-1, 4):
            x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
            segment = tuple(sorted(((x1, y1), (x2, y2))))
            if segment in seen_segments:
                continue
            seen_segments.add(segment)

            first = find_nearest_block((x1, y1), blocks, max_dist=35)
            second = find_nearest_block((x2, y2), blocks, max_dist=35)
            if not first or not second or first["id"] == second["id"]:
                continue

            first_ink = endpoint_ink(x1, y1)
            second_ink = endpoint_ink(x2, y2)
            pair = tuple(sorted((int(first["id"]), int(second["id"]))))

            if abs(first_ink - second_ink) >= 6:
                if first_ink > second_ink:
                    source, target = second, first
                    vector = ((x2, y2), (x1, y1))
                else:
                    source, target = first, second
                    vector = ((x1, y1), (x2, y2))
            else:
                # Top-to-bottom flowchart convention fallback when ink is balanced
                f_type, s_type = first.get("type"), second.get("type")
                if f_type == "start_end" and first["center"][1] < second["center"][1]:
                    source, target = first, second
                elif s_type == "start_end" and second["center"][1] < first["center"][1]:
                    source, target = second, first
                elif f_type == "start_end" and first["center"][1] > second["center"][1]:
                    source, target = second, first
                elif s_type == "start_end" and second["center"][1] > first["center"][1]:
                    source, target = first, second
                elif first["center"][1] <= second["center"][1]:
                    source, target = first, second
                else:
                    source, target = second, first
                vector = ((x1, y1), (x2, y2)) if source["id"] == first["id"] else ((x2, y2), (x1, y1))

            direction = (int(source["id"]), int(target["id"]))
            votes[pair][direction] += 1
            vectors[pair][direction] = vector

    for pair, direction_votes in votes.items():
        total = sum(direction_votes.values())
        ranked = direction_votes.most_common()
        best_dir, best_count = ranked[0]
        confidence = best_count / total
        if confidence < 0.5:
            unresolved_pairs.add(pair)
            continue
        connections.append({
            "from": best_dir[0],
            "to": best_dir[1],
            "vector": vectors[pair][best_dir],
            "branch": "",
            "confidence": round(confidence, 2),
            "uncertain": False,
        })

    # Connected component route recovery for multi-segment, loop-back, and merging routes
    route_mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
    )
    component_count, component_labels, component_stats, _ = cv2.connectedComponentsWithStats(
        (route_mask > 0).astype(np.uint8), 8
    )
    routed_pairs = set()
    for component_id in range(1, component_count):
        component_x, component_y, component_w, component_h, area = component_stats[component_id]
        if area < 30:
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
            x, y, w, h = block["bbox"]
            dx = np.maximum(np.maximum(x - xs, 0), xs - (x + w))
            dy = np.maximum(np.maximum(y - ys, 0), ys - (y + h))
            distances = np.hypot(dx, dy)
            index = int(np.argmin(distances))
            distance = float(distances[index])
            if distance <= 15:
                ex, ey = int(xs[index]), int(ys[index])
                radius = 10
                crop = mask[max(0, ey - radius):ey + radius + 1, max(0, ex - radius):ex + radius + 1]
                ink = int(np.count_nonzero(crop))
                endpoints.append({
                    "block": block,
                    "point": (ex, ey),
                    "dist": distance,
                    "ink": ink,
                })

        if len(endpoints) < 2:
            continue

        # Highest ink is the arrowhead/target; lower ink endpoints are sources
        endpoints.sort(key=lambda ep: ep["ink"], reverse=True)

        if len(endpoints) == 2:
            target_ep = endpoints[0]
            source_ep = endpoints[1]
            t_block = target_ep["block"]
            s_block = source_ep["block"]
            if t_block.get("type") == "start_end" and t_block["center"][1] < s_block["center"][1]:
                target_ep, source_ep = source_ep, target_ep

            diff = target_ep["ink"] - source_ep["ink"]
            conf = max(0.4, min(1.0, round(diff / max(1, target_ep["ink"]), 2)))
            dir_pair = (int(source_ep["block"]["id"]), int(target_ep["block"]["id"]))
            pair = tuple(sorted(dir_pair))
            routed_pairs.add(pair)

            connections.append({
                "from": dir_pair[0],
                "to": dir_pair[1],
                "vector": (source_ep["point"], target_ep["point"]),
                "branch": "",
                "confidence": conf,
                "uncertain": False,
            })
        else:
            # Multi-endpoint (merging branches or loopback T-junctions)
            target_ep = endpoints[0]
            for source_ep in endpoints[1:]:
                dir_pair = (int(source_ep["block"]["id"]), int(target_ep["block"]["id"]))
                pair = tuple(sorted(dir_pair))
                routed_pairs.add(pair)
                connections.append({
                    "from": dir_pair[0],
                    "to": dir_pair[1],
                    "vector": (source_ep["point"], target_ep["point"]),
                    "branch": "",
                    "confidence": 0.8,
                    "uncertain": False,
                })

    unresolved_pairs.difference_update(routed_pairs)

    connections = deduplicate_connections(connections)

    if not connections:
        warnings.append("No directed arrows could be reconstructed confidently. Connect the detected nodes manually.")
    detected_pairs = {tuple(sorted((int(edge["from"]), int(edge["to"])))) for edge in connections}
    for first_id, second_id in unresolved_pairs - detected_pairs:
        warnings.append(
            f"A possible connection between shapes {first_id} and {second_id} has no clear arrow direction; it was omitted. Review it manually."
        )
    connected_ids = {
        int(node_id)
        for edge in connections
        for node_id in (edge["from"], edge["to"])
    }
    if connections and any(int(block["id"]) not in connected_ids for block in blocks):
        warnings.append("Some detected shapes have no confirmed arrow connection; review the graph before generating code.")
    return connections, warnings

def find_nearest_block(point, blocks, max_dist=120):
    px, py = point
    min_d = float('inf')
    best = None
    for b in blocks:
        x, y, w, h = b["bbox"]
        dx = max(x - px, 0, px - (x + w))
        dy = max(y - py, 0, py - (y + h))
        d = np.hypot(dx, dy)
        if d < min_d and d <= max_dist:
            min_d = d
            best = b
    return best

def deduplicate_connections(connections):
    unique = []
    for c in connections:
        # Avoid exact duplicate edges
        if any(u["from"] == c["from"] and u["to"] == c["to"] for u in unique):
            continue
        # Check if reverse edge already exists on the same physical path
        rev = (c["to"], c["from"])
        existing_rev = [u for u in unique if u["from"] == rev[0] and u["to"] == rev[1]]
        if existing_rev and is_duplicate_reverse(existing_rev[0].get("vector"), c.get("vector")):
            if c.get("confidence", 0) > existing_rev[0].get("confidence", 0):
                unique.remove(existing_rev[0])
                unique.append(c)
            continue
        unique.append(c)
    return unique

def overlay_detections(img, blocks, connections):
    """
    Renders bounding boxes, shape labels, and connector arrows on top of the image.
    """
    overlay = img.copy()
    color_map = {
        "start_end": (0, 255, 0),
        "process": (255, 165, 0),
        "decision": (0, 255, 255),
        "input_output": (255, 0, 255),
        "manual_input": (180, 80, 255),
        "database": (0, 140, 255),
        "document": (255, 200, 0),
        "connector": (180, 180, 180),
        "offpage": (80, 80, 255),
        "predefined_process": (255, 100, 80),
        "delay": (0, 200, 220),
    }

    # Draw connection lines
    for conn in connections:
        p1, p2 = conn["vector"]
        cv2.arrowedLine(overlay, p1, p2, (0, 0, 255), 2, tipLength=0.2)

    # Draw block bounding boxes and labels
    for b in blocks:
        x, y, w, h = b["bbox"]
        color = color_map.get(b["type"], (255, 255, 255))
        cv2.rectangle(overlay, (x, y), (x + w, y + h), color, 2)
        label = f"#{b['id']} [{b['type']}]"
        cv2.putText(overlay, label, (x, max(15, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    return overlay
