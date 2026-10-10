import os
import re
import shutil
import subprocess
import cv2
import pytesseract

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
    confident_words = [(text, confidence) for text, confidence in words if confidence >= 60]
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

    text, _ = max(candidates, key=lambda candidate: candidate[1])
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

def clean_ocr_text(raw_text):
    """
    Normalizes common OCR misreadings in flowcharts.
    """
    cleaned = raw_text.strip()
    cleaned = re.sub(r'[\r\n]+', ' ', cleaned)
    
    # Fix keyword typos
    cleaned = re.sub(r'\b[iI][nN][pP][uU][tT]\b', 'Input', cleaned)
    cleaned = re.sub(r'\b[pP][rR][iI][nN][tT]\b', 'Print', cleaned)
    cleaned = re.sub(r'\b[sS][tT][aA][rR][tT]\b', 'Start', cleaned)
    cleaned = re.sub(r'\b[eE][nN][dD]\b', 'End', cleaned)
    
    return cleaned


init_tesseract()
