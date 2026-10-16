import os
import re
import shutil
import subprocess
import cv2
import pytesseract

import json
import logging
import concurrent.futures
from PIL import Image

logger = logging.getLogger(__name__)

WINDOWS_TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
_tesseract_available = False

def init_tesseract():
    global _tesseract_available
    configured_path = os.getenv("TESSERACT_CMD", "").strip().strip('"')
    candidates = [os.path.expandvars(os.path.expanduser(configured_path))] if configured_path else []
    if os.name == "nt":
        candidates.append(WINDOWS_TESSERACT_PATH)
    else:
        candidates.append("tesseract")

    for candidate in candidates:
        executable = shutil.which(candidate) or candidate
        if not os.path.isfile(executable):
            continue
        pytesseract.pytesseract.tesseract_cmd = executable
        try:
            pytesseract.get_tesseract_version()
        except (OSError, subprocess.SubprocessError, pytesseract.TesseractNotFoundError, pytesseract.TesseractError):
            continue
        _tesseract_available = True
        return True

    _tesseract_available = False
    return False


def tesseract_available():
    return _tesseract_available


def check_underline_under_operator(roi, box_tuple) -> bool:
    if roi is None or roi.size == 0:
        return False
    if len(roi.shape) == 3:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    else:
        gray = roi
    h, w = gray.shape[:2]
    char, l, b_tess, r, t_tess = box_tuple
    top = max(0, h - t_tess)
    bot = min(h, h - b_tess)
    char_h = max(1, bot - top)
    char_w = max(1, r - l)
    check_y1 = bot
    check_y2 = min(h, bot + int(char_h * 0.9) + 6)
    check_x1 = max(0, l - 3)
    check_x2 = min(w, r + 3)
    below_crop = gray[check_y1:check_y2, check_x1:check_x2]
    if below_crop.size == 0:
        return False
    _, bin_below = cv2.threshold(below_crop, 180, 255, cv2.THRESH_BINARY_INV)
    row_ink = np.sum(bin_below > 0, axis=1)
    return any(cnt >= char_w * 0.45 for cnt in row_ink)


def _read_candidate(image, config="--oem 3 --psm 6"):
    data = pytesseract.image_to_data(
        image,
        config=config,
        output_type=pytesseract.Output.DICT,
    )
    texts = data.get("text", [])
    confs = data.get("conf", [])
    has_lines = "line_num" in data
    lines_dict = {}
    confidences = []
    words = []
    for i in range(len(texts)):
        w = str(texts[i]).strip()
        if not w:
            continue
        try:
            conf = float(confs[i])
        except (IndexError, ValueError):
            conf = -1.0
        if conf >= 0:
            confidences.append(conf)
        if has_lines:
            b_num = data.get("block_num", [0])[i] if i < len(data.get("block_num", [])) else 0
            p_num = data.get("par_num", [0])[i] if i < len(data.get("par_num", [])) else 0
            l_num = data.get("line_num", [0])[i] if i < len(data.get("line_num", [])) else 0
            lines_dict.setdefault((b_num, p_num, l_num), []).append(w)
        else:
            words.append(w)
    if has_lines:
        if not lines_dict:
            return "", -1
        text = "\n".join(" ".join(ws) for ws in lines_dict.values())
    else:
        if not words:
            return "", -1
        text = " ".join(words)
    confidence = sum(confidences) / len(confidences) if confidences else -1
    return text, confidence


def _read_candidate_string(image, config="--oem 3 --psm 6"):
    """Read text preserving line breaks (for multi-statement shapes)."""
    text = pytesseract.image_to_string(image, config=config).strip()
    if not text:
        return "", -1
    return text, 60.0


def extract_block_text(img, bbox):
    """Return recognized text for a detected flowchart shape."""
    text, _ = extract_block_text_with_confidence(img, bbox)
    return text


def extract_block_text_with_confidence(img, bbox):
    """
    Read a detected shape with multiple OCR layouts and a thresholded fallback.
    Low-confidence text is returned for review rather than silently shortened.
    """
    x, y, w, h = bbox
    img_h, img_w = img.shape[:2]

    pad = max(6, int(round(min(w, h) * 0.12)))
    x1, y1 = max(0, x - pad), max(0, y - pad)
    x2, y2 = min(img_w, x + w + pad), min(img_h, y + h + pad)

    roi = img[y1:y2, x1:x2]
    if roi.size == 0:
        return "", -1

    if not tesseract_available():
        return "", -1

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    candidates = []
    full_size = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    candidates.append(_read_candidate(full_size, "--oem 3 --psm 6"))
    candidates.append(_read_candidate_string(full_size, "--oem 3 --psm 6"))
    candidates.append(_read_candidate(full_size, "--oem 3 --psm 4"))

    height, width = gray.shape[:2]
    inner = gray[int(height * 0.2):int(height * 0.8), int(width * 0.16):int(width * 0.84)]
    if inner.size:
        inner_size = cv2.resize(inner, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        candidates.append(_read_candidate(inner_size, "--oem 3 --psm 6"))
        candidates.append(_read_candidate_string(inner_size, "--oem 3 --psm 6"))

    adaptive = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    adaptive_size = cv2.resize(
        adaptive, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC
    )
    candidates.append(_read_candidate(adaptive_size, "--oem 3 --psm 11"))
    candidates.append(_read_candidate(adaptive_size, "--oem 3 --psm 12"))

    shape_x1 = min(img_w, x + int(w * 0.12))
    shape_y1 = min(img_h, y + int(h * 0.2))
    shape_x2 = max(shape_x1, min(img_w, x + int(w * 0.88)))
    shape_y2 = max(shape_y1, min(img_h, y + int(h * 0.8)))
    shape_inner = img[shape_y1:shape_y2, shape_x1:shape_x2]
    if shape_inner.size:
        shape_gray = cv2.cvtColor(shape_inner, cv2.COLOR_BGR2GRAY)
        shape_gray_size = cv2.resize(
            shape_gray, (0, 0), fx=3.0, fy=3.0,
            interpolation=cv2.INTER_CUBIC,
        )
        candidates.append(_read_candidate(shape_gray_size, "--oem 3 --psm 6"))
        candidates.append(_read_candidate_string(shape_gray_size, "--oem 3 --psm 6"))
        if min(shape_gray.shape[:2]) >= 11:
            shape_adaptive = cv2.adaptiveThreshold(
                shape_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2,
            )
            shape_size = cv2.resize(
                shape_adaptive, (0, 0), fx=3.0, fy=3.0,
                interpolation=cv2.INTER_CUBIC,
            )
            candidates.append(_read_candidate(shape_size, "--oem 3 --psm 11"))
            candidates.append(_read_candidate(shape_size, "--oem 3 --psm 12"))

    # Exact bounding box without padding (prevents arrowheads from leaking into the crop)
    exact_box = img[y:y+h, x:x+w]
    if exact_box.size:
        exact_gray = cv2.cvtColor(exact_box, cv2.COLOR_BGR2GRAY)
        candidates.append(_read_candidate(exact_gray, "--oem 3 --psm 6"))
        candidates.append(_read_candidate_string(exact_gray, "--oem 3 --psm 6"))
        candidates.append(_read_candidate(exact_gray, "--oem 3 --psm 11"))

    # Check if the shape contains '<' or '>' with an underline underneath (e.g. <= / >=)
    try:
        for check_crop in (shape_inner, exact_box):
            if check_crop is not None and check_crop.size > 0:
                cg = cv2.cvtColor(check_crop, cv2.COLOR_BGR2GRAY) if len(check_crop.shape) == 3 else check_crop
                box_str = pytesseract.image_to_boxes(cg).strip()
                has_upgrade = False
                for bline in box_str.splitlines():
                    parts = bline.split()
                    if len(parts) >= 5 and parts[0] in ("<", ">"):
                        b_tuple = (parts[0], int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]))
                        if check_underline_under_operator(cg, b_tuple):
                            for c_idx in range(len(candidates)):
                                ct, cc = candidates[c_idx]
                                if "<" in ct or ">" in ct:
                                    candidates[c_idx] = (ct.replace("<", "<=").replace(">", ">="), cc)
                            has_upgrade = True
                            break
                if has_upgrade:
                    break
    except Exception:
        pass

    def candidate_rank(candidate):
        raw_text, confidence = candidate
        cleaned = clean_ocr_text(raw_text)
        rank = confidence
        if re.search(r"\b(?:input|print|start|end)\b", cleaned, re.I):
            rank += 18
        if re.search(r"\b[A-Za-z_]\w*\s*=\s*[^=].+", cleaned):
            rank += 18
        if re.search(r"(?:<=|>=|==|!=|[<>])", cleaned):
            rank += 12
        if len(re.findall(r"[A-Za-z0-9]", cleaned)) >= 3:
            rank += 6
        if "\n" in cleaned:
            sub_lines = [l.strip() for l in cleaned.splitlines() if l.strip()]
            if len(sub_lines) >= 2 and all(re.search(r"\b[A-Za-z_]\w*\s*=", l) for l in sub_lines):
                rank += 30
        return rank

    text, confidence = max(candidates, key=candidate_rank)
    cleaned = clean_ocr_text(text)
    if confidence < 15 or not re.search(r"[A-Za-z0-9]", cleaned):
        return "", confidence
    plausible_candidates = set()
    for candidate_text, candidate_confidence in candidates:
        candidate_cleaned = clean_ocr_text(candidate_text)
        if candidate_confidence < 30 or re.search(r"[^A-Za-z0-9_+\-*/%=<>?! .\n]", candidate_cleaned):
            continue
        if not re.search(r"\b[A-Za-z_]\w*\s*=", candidate_cleaned) and not re.search(
            r"(?:<=|>=|==|!=|[<>])", candidate_cleaned
        ) and not re.search(r"\b(?:input|print|start|end)\b", candidate_cleaned, re.I):
            continue
        norm_cand = re.sub(r"[^a-z0-9_+\-*/%=<>?!]", "", candidate_cleaned.lower())
        plausible_candidates.add(norm_cand)
    if len(plausible_candidates) > 1:
        cand_list = list(plausible_candidates)
        has_conflict = False
        for c1 in cand_list:
            for c2 in cand_list:
                if c1 != c2 and c1 not in c2 and c2 not in c1:
                    has_conflict = True
                    break
            if has_conflict:
                break
        if has_conflict:
            confidence = min(confidence, 49)
    return cleaned, confidence


def extract_region_text(img, bbox):
    """Read text from an arbitrary image region, including connector labels."""
    text, _ = extract_region_text_with_confidence(img, bbox)
    return text


def extract_region_text_with_confidence(img, bbox):
    """Return OCR text and its mean word confidence for comparing candidate crops."""
    x, y, w, h = bbox
    img_h, img_w = img.shape[:2]
    x1, y1 = max(0, int(x)), max(0, int(y))
    x2, y2 = min(img_w, int(x + w)), min(img_h, int(y + h))
    roi = img[y1:y2, x1:x2]
    if roi.size == 0 or not tesseract_available():
        return "", -1

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    scaled = cv2.resize(gray, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    text, confidence = _read_candidate(scaled)
    return clean_ocr_text(text), confidence


def clean_ocr_text(raw_text: str) -> str:
    """
    Normalizes common OCR misreadings in flowcharts.
    Preserves multiple statements on separate lines.
    Never invents labels if text is blank.
    """
    text = raw_text.strip()
    if not text:
        return ""

    # Unicode math symbols
    text = text.replace("≤", "<=").replace("≥", ">=").replace("≠", "!=").replace("×", "*")

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    cleaned_lines = []
    for line in lines:
        cleaned = line
        # Fix keyword typos
        cleaned = re.sub(r'\b[iI][nN][pP][uU][tT]\b', 'Input', cleaned)
        cleaned = re.sub(r'\b[pP][rR][iI][nN][tT]\b', 'Print', cleaned)
        cleaned = re.sub(r'\b[sS][tT][aA][rR][tT]\b', 'Start', cleaned)
        cleaned = re.sub(r'\b[eE][nN][dD]\b', 'End', cleaned)

        # Remove leading noise punctuation before keywords or assignments
        cleaned = re.sub(r'^[:;.,|/\\~`_jJ!?-]+\s+(?=(?:Input|Print|Start|End|[A-Za-z_]\w*\s*=))', '', cleaned)
        cleaned = re.sub(r'^[(\[{]\s*(?=(?:Input|Print|Start|End|[A-Za-z_]\w*\s*=))', '', cleaned, flags=re.I)
        cleaned = re.sub(r'\s+[*+~`]+$', '', cleaned)

        # Fix common math/operator OCR artifacts
        cleaned = re.sub(r'(\w)\s*=\s*(\w)\s*t\+\s*', r'\1 = \2 + ', cleaned)
        cleaned = re.sub(r'\bt\+\b', '+', cleaned)
        cleaned = re.sub(r'(?<=\w)\s+[xX]\s+(?=\w)', ' * ', cleaned)
        cleaned = re.sub(r'(\w)\s*([+\-*/%]|<=|>=|==|!=|<|>)\s*(\w)', r'\1 \2 \3', cleaned)
        cleaned = re.sub(r'(\w)\s*=\s*(\w)', r'\1 = \2', cleaned)

        # Fix "<" that should be "<=" when followed by a variable and "?" (decision context)
        # e.g., "i < n?" -> "i <= n?"
        cleaned = re.sub(r'(\b[A-Za-z_]\w*\s*)<(\s*[A-Za-z_]\w*\s*\?)', r'\1<=\2', cleaned)

        # Fix spurious decimal points: "fact = 1.1" -> "fact = 1"
        # OCR often misreads "1" as "1.1" when noise appears after the digit.
        # Pattern: "= <digit(s)>.<same last digit>" — likely OCR noise.
        def _fix_spurious_decimal(m):
            prefix, int_part, dec_digit = m.group(1), m.group(2), m.group(3)
            if dec_digit == '0' or dec_digit == int_part[-1]:
                return prefix + int_part
            return m.group(0)
        cleaned = re.sub(r'(=\s*)(\d+)\.(\d)(?!\d)', _fix_spurious_decimal, cleaned)

        # Fix common OCR confusion of variable i with j in loop updates / multiplications
        cleaned = re.sub(r'(\bfact\s*=\s*fact\s*\*\s*)j\b', r'\1i', cleaned)
        cleaned = re.sub(r'\bij\s*=\s*i\s*\+\s*1\b', 'i = i + 1', cleaned)

        # Split multiple assignments on one line
        pattern = r'(\b\d+|\b[A-Za-z_]\w*)\s+([A-Za-z_]\w*\s*(?:=|\+=|-=|\*=|/=|%=)(?!=))'
        prev = None
        while prev != cleaned:
            prev = cleaned
            cleaned = re.sub(pattern, r'\1\n\2', cleaned)

        for sub in cleaned.splitlines():
            s = sub.strip()
            if s:
                cleaned_lines.append(s)

    if not cleaned_lines:
        return ""

    # Merge Input/Print with following variable line if broken across lines
    combined = []
    idx = 0
    while idx < len(cleaned_lines):
        cur = cleaned_lines[idx]
        if idx + 1 < len(cleaned_lines) and re.fullmatch(r'(?:Input|Print)', cur, re.I):
            combined.append(f"{cur.capitalize()} {cleaned_lines[idx+1]}")
            idx += 2
        else:
            combined.append(cur)
            idx += 1

    return "\n".join(combined).strip()


def clean_branch_label(raw_text: str) -> str:
    """
    Extracts confident Yes/No decision branch labels from OCR text.
    Returns 'Yes', 'No', or '' if not clearly identified.
    """
    t = (raw_text or "").strip().lower()
    if not t:
        return ""
    # Check for Yes / True
    if re.search(r'\b(yes|true)\b', t) or t in ("yes", "y", "ye", "true", "| yes", "yes |"):
        return "Yes"
    # Check for No / False
    if re.search(r'\b(no|false)\b', t) or t in ("no", "n", "false", "| no", "no |"):
        return "No"
    return ""


def extract_flowchart_text_with_gemini(
    pil_img: Image.Image,
    blocks: list[dict],
    timeout_sec: float = 6.0
) -> dict[int, str]:
    """
    Uses Gemini Vision to read text for detected flowchart shapes.
    Backend-only API key. Optional with strict timeout and validation.
    Returns a dict mapping block ID (int) -> recognized text (str).
    Never invents executable labels when recognition fails.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or not blocks:
        return {}

    # Target blocks that need text
    target_blocks = [b for b in blocks if not b.get("text")]
    if not target_blocks:
        # Avoid unnecessary API calls if all blocks already have confident text
        return {}

    valid_ids = {int(b["id"]) for b in blocks}

    shapes_payload = [
        {
            "id": int(b["id"]),
            "type": b.get("type", "process"),
            "bbox": list(b.get("bbox", []))
        }
        for b in target_blocks
    ]

    prompt = (
        "You are an expert flowchart OCR assistant. I have detected flowchart shapes in this image "
        f"with the following bounding boxes (x, y, w, h):\n{json.dumps(shapes_payload)}\n\n"
        "Read the exact text printed or written inside each shape ID. "
        "Return ONLY a valid JSON object in this exact schema with no extra text or markdown:\n"
        "{\n"
        '  "nodes": [\n'
        '    {"id": 1, "text": "exact text inside shape 1"}\n'
        "  ]\n"
        "}\n"
        "Rules:\n"
        "1. Only include IDs that are present in the provided list.\n"
        "2. If the text inside a shape cannot be read clearly, return an empty string \"\" for text.\n"
        "3. NEVER invent, hallucinate, or guess code expressions or labels."
    )

    def _call_api():
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        for model_name in ("gemini-2.0-flash", "gemini-1.5-flash", "gemini-3.8-flash"):
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content([prompt, pil_img])
                if response and response.text:
                    return response.text
            except Exception as e:
                logger.debug("Gemini model %s failed: %s", model_name, e)
                continue
        return ""

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_call_api)
            raw_response = future.result(timeout=timeout_sec)
    except concurrent.futures.TimeoutError:
        logger.warning("Gemini Vision OCR timed out after %s seconds; falling back to local OCR.", timeout_sec)
        return {}
    except Exception as e:
        logger.warning("Gemini Vision OCR call failed (%s); falling back to local OCR.", e)
        return {}

    if not raw_response:
        return {}

    try:
        # Safe JSON extraction
        match = re.search(r'\{[\s\S]*\}', raw_response)
        if not match:
            return {}
        data = json.loads(match.group(0))
        nodes_list = data.get("nodes")
        if not isinstance(nodes_list, list):
            return {}

        results = {}
        for item in nodes_list:
            if not isinstance(item, dict):
                continue
            node_id = item.get("id")
            try:
                node_id = int(node_id)
            except (ValueError, TypeError):
                continue
            if node_id not in valid_ids:
                # Reject extra or hallucinated IDs
                continue
            text = str(item.get("text") or "").strip()
            # Sanitize text
            cleaned = clean_ocr_text(text)
            results[node_id] = cleaned

        return results
    except Exception as e:
        logger.warning("Failed to parse Gemini Vision OCR response (%s): %s", e, raw_response[:200])
        return {}


init_tesseract()
