import cv2
import numpy as np
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
    
    if num_vertices == 4:
        # Measure corner angles
        pts = approx.reshape(4, 2)
        angles = []
        for i in range(4):
            p1 = pts[i]
            p2 = pts[(i + 1) % 4]
            p3 = pts[(i + 2) % 4]
            v1 = p1 - p2
            v2 = p3 - p2
            cosine = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-5)
            angle = np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))
            angles.append(angle)

        mean_angle = np.mean(angles)
        
        if 82 <= mean_angle <= 98 and 0.2 <= aspect_ratio <= 5.0:
            return "process"  # Rectangle
        elif 0.75 <= aspect_ratio <= 1.35 and circularity < 0.68:
            return "decision"  # Diamond
        else:
            return "input_output"  # Parallelogram / Slanted shape

    elif num_vertices > 5:
        if circularity > 0.65:
            return "start_end"  # Oval / Stadium / Circle
        else:
            return "process"

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
    Removes inner contours nested inside larger blocks.
    """
    blocks = sorted(blocks, key=lambda b: b["area"], reverse=True)
    kept = []
    
    for b in blocks:
        x1, y1, w1, h1 = b["bbox"]
        is_contained = False
        for k in kept:
            kx, ky, kw, kh = k["bbox"]
            if x1 >= kx and y1 >= ky and (x1 + w1) <= (kx + kw) and (y1 + h1) <= (ky + kh):
                is_contained = True
                break
        if not is_contained:
            kept.append(b)
            
    # Re-assign clean sequential IDs sorted top-to-bottom
    kept = sorted(kept, key=lambda b: b["bbox"][1])
    for i, b in enumerate(kept):
        b["id"] = i + 1
        
    return kept

def detect_connections(thresh_img, blocks):
    """
    Detects directional connections between blocks using line vectors and spatial proximity.
    """
    connections = []
    if len(blocks) < 2:
        return connections

    # Mask symbol areas to isolate arrow shafts
    mask = thresh_img.copy()
    for block in blocks:
        x, y, w, h = block["bbox"]
        cv2.rectangle(mask, (max(0, x - 8), max(0, y - 8)), (x + w + 8, y + h + 8), 0, -1)

    lines = cv2.HoughLinesP(mask, 1, np.pi / 180, threshold=20, minLineLength=15, maxLineGap=10)

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            start_b = find_nearest_block((x1, y1), blocks)
            end_b = find_nearest_block((x2, y2), blocks)

            if start_b and end_b and start_b["id"] != end_b["id"]:
                connections.append({
                    "from": start_b["id"],
                    "to": end_b["id"],
                    "vector": ((x1, y1), (x2, y2))
                })

    # Fallback spatial proximity connection if Hough lines miss
    if not connections:
        for i in range(len(blocks) - 1):
            connections.append({
                "from": blocks[i]["id"],
                "to": blocks[i + 1]["id"],
                "vector": (blocks[i]["center"], blocks[i + 1]["center"])
            })

    return deduplicate_connections(connections)

def find_nearest_block(point, blocks, max_dist=120):
    px, py = point
    min_d = float('inf')
    best = None
    for b in blocks:
        bx, by = b["center"]
        d = np.hypot(px - bx, py - by)
        if d < min_d and d <= max_dist:
            min_d = d
            best = b
    return best

def deduplicate_connections(connections):
    seen = set()
    unique = []
    for c in connections:
        pair = (c["from"], c["to"])
        if pair not in seen:
            seen.add(pair)
            unique.append(c)
    return unique

def overlay_detections(img, blocks, connections):
    """
    Renders bounding boxes, shape labels, and connector arrows on top of the image.
    """
    overlay = img.copy()
    color_map = {
        "start_end": (0, 255, 0),     # Green
        "process": (255, 165, 0),      # Blue/Orange
        "decision": (0, 255, 255),    # Yellow
        "input_output": (255, 0, 255) # Magenta
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
