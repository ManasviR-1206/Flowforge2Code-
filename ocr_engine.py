import os
import re
import shutil
import cv2
import pytesseract
from PIL import Image

# Locate Tesseract on Windows automatically if standard installation exists
COMMON_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
]

def init_tesseract():
    for p in COMMON_TESSERACT_PATHS:
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            return True
    return False


def tesseract_available():
    command = pytesseract.pytesseract.tesseract_cmd
    return os.path.isfile(command) or shutil.which(command) is not None


# Initialize on import
init_tesseract()

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

    return extract_region_text(img, (x1, y1, x2 - x1, y2 - y1))


def extract_region_text(img, bbox):
    """Read text from an arbitrary image region, including connector labels."""
    x, y, w, h = bbox
    img_h, img_w = img.shape[:2]
    x1, y1 = max(0, int(x)), max(0, int(y))
    x2, y2 = min(img_w, int(x + w)), min(img_h, int(y + h))
    roi = img[y1:y2, x1:x2]
    if roi.size == 0 or not tesseract_available():
        return ""

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    scaled = cv2.resize(gray, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    filtered = cv2.bilateralFilter(scaled, 7, 50, 50)
    _, thresh = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    raw_text = ""
    try:
        for psm in ("7", "6", "11", "8"):
            raw_text = pytesseract.image_to_string(thresh, config=f"--psm {psm}")
            if raw_text.strip():
                break
    except Exception:
        raw_text = ""

    return clean_ocr_text(raw_text)

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
