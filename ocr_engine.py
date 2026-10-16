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


def _read_candidate(image):
    data = pytesseract.image_to_data(
        image,
        config="--oem 3 --psm 6",
        output_type=pytesseract.Output.DICT,
    )
    words = [
        (text.strip(), float(confidence))
        for text, confidence in zip(data["text"], data["conf"])
        if text.strip()
    ]
    confident_words = [(text, confidence) for text, confidence in words if confidence >= 50]
    selected_words = confident_words or words
    if not selected_words:
        return "", -1
    text = " ".join(word for word, _ in selected_words)
    confidence = sum(score for _, score in selected_words) / len(selected_words)
    return text, confidence


def extract_block_text(img, bbox):
    """
    Crops ROI bounding box, expands padding, applies bilateral filtering,
    and extracts text using Tesseract OCR.
    Never invents executable labels when recognition fails.
    """
    x, y, w, h = bbox
    img_h, img_w = img.shape[:2]

    pad = 6
    x1, y1 = max(0, x - pad), max(0, y - pad)
    x2, y2 = min(img_w, x + w + pad), min(img_h, y + h + pad)

    roi = img[y1:y2, x1:x2]
    if roi.size == 0:
        return ""

    if not tesseract_available():
        return ""

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    candidates = []
    full_size = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    candidates.append(_read_candidate(full_size))

    height, width = gray.shape[:2]
    inner = gray[int(height * 0.2):int(height * 0.8), int(width * 0.16):int(width * 0.84)]
    if inner.size:
        inner_size = cv2.resize(inner, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        candidates.append(_read_candidate(inner_size))

    text, conf = max(candidates, key=lambda candidate: candidate[1])
    if conf < 30 or not re.search(r'[A-Za-z0-9]', text):
        return ""
    return clean_ocr_text(text)


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
    Never invents labels if text is blank.
    """
    cleaned = raw_text.strip()
    cleaned = re.sub(r'[\r\n]+', ' ', cleaned)
    
    # Fix keyword typos
    cleaned = re.sub(r'\b[iI][nN][pP][uU][tT]\b', 'Input', cleaned)
    cleaned = re.sub(r'\b[pP][rR][iI][nN][tT]\b', 'Print', cleaned)
    cleaned = re.sub(r'\b[sS][tT][aA][rR][tT]\b', 'Start', cleaned)
    cleaned = re.sub(r'\b[eE][nN][dD]\b', 'End', cleaned)
    
    # Fix common math/operator OCR artifacts
    cleaned = re.sub(r'(\w)\s*=\s*(\w)\s*t\+\s*', r'\1 = \2 + ', cleaned)
    cleaned = re.sub(r'\bt\+\b', '+', cleaned)
    cleaned = re.sub(r'(\w)\s*([+\-*/%]|<=|>=|==|!=|<|>)\s*(\w)', r'\1 \2 \3', cleaned)
    cleaned = re.sub(r'(\w)\s*=\s*(\w)', r'\1 = \2', cleaned)
    
    return cleaned.strip()


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

