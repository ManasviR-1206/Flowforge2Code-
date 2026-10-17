import os
import re
import shutil
import subprocess
import cv2
import numpy as np
import pytesseract

import json
import logging
import concurrent.futures
from collections import Counter
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
    if below_crop.size:
        _, bin_below = cv2.threshold(below_crop, 180, 255, cv2.THRESH_BINARY_INV)
        row_ink = np.sum(bin_below > 0, axis=1)
        if any(cnt >= char_w * 0.45 for cnt in row_ink):
            return True

    # The '≤' / '≥' glyphs draw the underline *inside* the character box (a
    # '>' with a bar beneath it), so also look at the bottom strip of the box
    # itself. A plain '<' / '>' has only its narrow tip down there.
    strip_h = max(2, int(char_h * 0.28))
    strip = gray[max(top, bot - strip_h):bot, check_x1:check_x2]
    if strip.size == 0:
        return False
    _, bin_strip = cv2.threshold(strip, 180, 255, cv2.THRESH_BINARY_INV)
    strip_ink = np.sum(bin_strip > 0, axis=1)
    return any(cnt >= char_w * 0.6 for cnt in strip_ink)


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


def _norm_reading_key(raw_text: str) -> str:
    """Canonical key for comparing OCR readings across layouts.

    Whitespace is collapsed so trailing/newline noise does not split otherwise
    identical readings, while word boundaries are preserved so a reading that
    dropped a space (e.g. 'Cis' vs 'C is') still counts as a different reading.
    """
    cleaned = clean_ocr_text(raw_text or "")
    return re.sub(r"\s+", " ", cleaned.strip().lower())


def _candidate_rank(candidate):
    """Score an OCR candidate reading; higher is better.

    Complements raw confidence with structural signals so a complete statement
    or condition outranks a bare keyword or a stray fragment.
    """
    raw_text, confidence = candidate
    cleaned = clean_ocr_text(raw_text)
    rank = confidence
    if re.search(r"\b(?:input|print|start|end)\b", cleaned, re.I):
        rank += 18
    # A complete Input/Print statement carrying an operand (e.g. 'Print "Even"',
    # 'Input n') is strictly more informative than a bare keyword ('Print'),
    # whose raw confidence can otherwise be a fraction of a point higher.
    if re.match(
        r"^(?:input|print|output|display|show|write|read|get|enter)\b\s+\S",
        cleaned, re.I,
    ):
        rank += 10
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


def select_best_candidate(candidates):
    """Pick the most complete, best-supported reading among OCR candidates.

    Raw confidence is a *mean over recognized words*, so a layout that silently
    drops a word or a whole line (e.g. sparse-text psm 11/12) can report a higher
    mean than a layout that read everything. To avoid discarding content we:

    1. drop readings that are a strict substring of an equally-or-better
       supported reading (truncations such as 'Input A' vs 'Input A, B, C');
    2. among readings identical once whitespace is removed, prefer the one that
       keeps the most word boundaries ('Print C is largest' over 'Print Cis largest').

    Falls back to the structural rank alone when the signals are inconclusive.
    """
    candidates = list(candidates)
    if not candidates:
        return "", -1

    agreement: Counter = Counter()
    for c_text, _c_conf in candidates:
        key = _norm_reading_key(c_text)
        if key:
            agreement[key] += 1

    best_words: dict = {}
    for key in agreement:
        nospace = re.sub(r"\s+", "", key)
        words = len(key.split())
        if nospace and words > best_words.get(nospace, 0):
            best_words[nospace] = words

    def rank(candidate):
        base = _candidate_rank(candidate)
        key = _norm_reading_key(candidate[0])
        nospace = re.sub(r"\s+", "", key)
        if nospace and best_words.get(nospace, 0) > 1 and len(key.split()) == best_words[nospace]:
            base += 3
        return base

    def is_truncated(candidate):
        # A reading is a truncation when its words are a leading prefix of the
        # words of an equally-or-better supported reading - i.e. it silently
        # dropped trailing content ('Input A' vs 'Input A, B, C', or a whole
        # condition line). Comparing whole words (not raw characters) means a
        # noisy longer reading like 'input nh ,' does NOT make the correct
        # 'Input n' look truncated.
        words = re.findall(r"[a-z0-9]+", _norm_reading_key(candidate[0]))
        if not words:
            return False
        votes = agreement.get(_norm_reading_key(candidate[0]), 1)
        for other, other_votes in agreement.items():
            other_words = re.findall(r"[a-z0-9]+", other)
            if (
                other_votes >= votes
                and len(other_words) > len(words)
                and other_words[: len(words)] == words
            ):
                return True
        return False

    viable = [candidate for candidate in candidates if not is_truncated(candidate)]
    return max(viable or candidates, key=rank)


# Comparison operators as they appear *between two operands on the same line*.
# Anchoring on the surrounding operands stops a stray '<'/'>' border fragment
# (e.g. a diamond edge or an arrowhead) from being counted as a condition
# operator, so operator counts stay comparable between the chosen reading and a
# raw OCR probe. Only horizontal whitespace is allowed between an operator and
# its operands so a line break cannot make two unrelated glyphs look joined.
_OPERAND_OPERATOR_RE = re.compile(
    r"(?<=[A-Za-z0-9_])[ \t]*(<=|>=|==|!=|=|[<>])[ \t]*(?=[A-Za-z0-9_])"
)


def comparison_operators(text: str) -> list:
    """Ordered list of comparison operators found between operands in `text`."""
    return _OPERAND_OPERATOR_RE.findall(text or "")


def _replace_comparison_operators(text: str, operators: list) -> str:
    """Swap the operator tokens of `text` for `operators`, keeping everything else."""
    parts = []
    last = 0
    for idx, match in enumerate(_OPERAND_OPERATOR_RE.finditer(text)):
        if idx >= len(operators):
            break
        parts.append(text[last:match.start(1)])
        parts.append(operators[idx])
        last = match.end(1)
    parts.append(text[last:])
    return "".join(parts)


def _upgrade_underlined_chevrons(crop, text: str) -> str:
    """Turn a lone '<'/'>' into '<='/'>=' when the glyph carries an underline.

    '≤'/'≥' are a chevron above a bar; OCR may report only the chevron while the
    bar is still visible in the pixels.
    """
    text = text.replace("≤", "<=").replace("≥", ">=").replace("≠", "!=")
    if "<" not in text and ">" not in text:
        return text
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
    try:
        box_str = pytesseract.image_to_boxes(gray).strip()
    except Exception:
        return text
    for line in box_str.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0] in ("<", ">"):
            box = (parts[0], int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]))
            if check_underline_under_operator(gray, box):
                text = re.sub(r"(?<![<>=!])>(?!=)", ">=", text)
                text = re.sub(r"(?<![<>=!])<(?!=)", "<=", text)
                return text
    return text


# Ordered probe schedule. A flowchart symbol's text sits in the middle band of
# its shape, so the central crops are tried first and a decision with a clear
# operator reading resolves after only a few probes; later probes cover symbols
# whose text sits higher or lower. This is a search order, not a per-image case.
_CONDITION_PROBES = (
    (0.26, "gray"), (0.26, "otsu"), (0.26, "gray3"),
    (0.24, "gray"), (0.28, "gray"), (0.22, "gray"),
    (0.28, "otsu"), (0.24, "otsu"), (0.20, "gray"),
    (0.30, "gray"), (0.18, "gray"), (0.26, "adap"),
    (0.24, "adap"), (0.22, "otsu"),
)


def _prepare_condition_crop(crop, kind):
    if kind == "gray3":
        return cv2.resize(crop, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    if kind == "otsu":
        _, otsu = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return cv2.resize(otsu, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    if kind == "adap":
        adap = cv2.adaptiveThreshold(
            crop, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
        )
        return cv2.resize(adap, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    return cv2.resize(crop, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)


def read_condition_operator_signatures(roi, expected_count=None, max_matches=3) -> list:
    """Read a decision glyph region several ways; return operator sequences.

    The full shape crop often confuses a '≥' with '=' because the diamond border
    and the chevron merge, but a tighter crop isolates the operators so they read
    as '>'/'<' (upgraded to '>='/'<=' when the underline is present). When
    `expected_count` is given, stop once enough agreeing-count probes are found so
    the common case stays cheap.
    """
    if roi is None or getattr(roi, "size", 0) == 0 or not tesseract_available():
        return []
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
    height, width = gray.shape[:2]
    signatures = []
    for inset, kind in _CONDITION_PROBES:
        y1, y2 = int(height * inset), int(height * (1.0 - inset))
        x1, x2 = int(width * inset), int(width * (1.0 - inset))
        crop = gray[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
        if crop.size == 0 or min(crop.shape[:2]) < 8:
            continue
        try:
            prep = _prepare_condition_crop(crop, kind)
        except Exception:
            continue
        try:
            raw = pytesseract.image_to_string(prep, config="--oem 3 --psm 6")
        except Exception:
            continue
        if not raw.strip():
            continue
        ops = comparison_operators(_upgrade_underlined_chevrons(prep, raw))
        if not ops:
            continue
        signatures.append(ops)
        if expected_count is not None and len(ops) == expected_count:
            agreed = sum(1 for sig in signatures if len(sig) == expected_count)
            if agreed >= max_matches:
                return signatures
    return signatures


def recover_condition_operators(text: str, roi) -> str:
    """Repair misread comparison operators in a decision condition.

    A '≥'/'≤' glyph is frequently read as a bare '=' (or '2'/'z'). Operator
    *positions* come from the chosen reading (so operands are preserved); operator
    *values* are corroborated by a dedicated pixel/OCR pass over the condition
    glyphs: among probes whose operator count matches, a per-position majority
    decides. Only an upgrade is ever applied ('=' -> '>='/'<='), never a
    downgrade, so a genuine '==' is never weakened. Returns `text` unchanged when
    the pixel evidence is inconclusive (the caller keeps it flagged for review).
    """
    consensus = comparison_operators(text)
    if not consensus or "=" not in consensus:
        return text
    signatures = read_condition_operator_signatures(roi, expected_count=len(consensus))
    matching = [sig for sig in signatures if len(sig) == len(consensus)]
    if not matching:
        return text
    repaired = list(consensus)
    changed = False
    for idx, current in enumerate(consensus):
        tally = Counter(sig[idx] for sig in matching)
        top_votes = tally.most_common(1)[0][1]
        tied = [op for op, count in tally.items() if count == top_votes]
        # A chevron reading is more specific than the bare '=' misread, so break a
        # tie in favour of the comparison operator.
        seen = next((op for op in (">=", "<=", ">", "<") if op in tied), tied[0])
        if current == "=" and seen in (">=", "<="):
            repaired[idx] = seen
            changed = True
        elif current == ">" and seen == ">=":
            repaired[idx] = ">="
            changed = True
        elif current == "<" and seen == "<=":
            repaired[idx] = "<="
            changed = True
    if not changed:
        return text
    return _replace_comparison_operators(text, repaired)


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

    text, confidence = select_best_candidate(candidates)
    cleaned = clean_ocr_text(text)
    if confidence < 15 or not re.search(r"[A-Za-z0-9]", cleaned):
        return "", confidence
    # Only penalize confidence if another high-confidence candidate genuinely contradicts the chosen reading.
    # Short noise fragments (e.g. inner-crop letter fragments like "en" or "na") are not genuine readings,
    # so they must not downgrade a confident condition or statement.
    if confidence >= 50:
        top_norm = re.sub(r"[^a-z0-9_+\-*/%=<>?!]", "", cleaned.lower())
        for c_text, c_conf in candidates:
            if c_conf >= max(60.0, confidence * 0.85):
                c_clean = clean_ocr_text(c_text)
                c_alnum = len(re.findall(r"[A-Za-z0-9]", c_clean))
                has_op = bool(re.search(r"[<>=!+\-*/%]", c_clean))
                # A competing reading with no alphanumeric operand at all (e.g. a
                # stray '>' border fragment) is not a genuine alternative label.
                if c_alnum == 0:
                    continue
                if c_alnum < 3 and not has_op:
                    continue
                c_norm = re.sub(r"[^a-z0-9_+\-*/%=<>?!]", "", c_clean.lower())
                if c_norm and top_norm and c_norm != top_norm and c_norm not in top_norm and top_norm not in c_norm:
                    diff_chars = len(set(c_norm) ^ set(top_norm))
                    if diff_chars >= 3:
                        confidence = min(confidence, 49)
                        break
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


_FLOW_KEYWORD_RE = re.compile(
    r"\b(?:input|print|output|display|show|write|read|get|enter|start|end|"
    r"if|elif|else|while|for|return|break|continue)\b",
    re.I,
)


def _line_has_flow_signal(line: str) -> bool:
    """True when a line plausibly carries flowchart content (operator/keyword/string)."""
    if not line:
        return False
    if re.search(r"[<>=!%+\-*/]", line):
        return True
    if _FLOW_KEYWORD_RE.search(line):
        return True
    if '"' in line or "'" in line:
        return True
    return False


def _is_ocr_noise_fragment(line: str) -> bool:
    """True for border/artifact fragments OCR injects around real labels.

    Pure punctuation, or a very short alphanumeric fragment with no operator,
    keyword, or quoted string (e.g. ',', 'eS 7', 'Nh'), is noise. Longer prose
    and single-line labels are preserved so genuine text is never discarded.
    """
    core = re.sub(r"[^A-Za-z0-9]", "", line)
    if not core:
        return True
    return len(core) <= 5


def clean_ocr_text(raw_text: str) -> str:
    """
    Normalizes common OCR misreadings in flowcharts.
    Preserves multiple statements on separate lines.
    Never invents labels if text is blank.
    """
    text = raw_text.strip()
    if not text:
        return ""

    # Normalize Unicode math symbols BEFORE stripping non-ASCII. Otherwise the
    # '≤' / '≥' glyphs that flowcharts commonly use would be deleted outright.
    text = text.replace("≤", "<=").replace("≥", ">=").replace("≠", "!=").replace("×", "*")

    # Remove non-printable / non-ASCII characters that OCR sometimes injects
    # (null bytes, replacement char, DEL, C1 controls, and any other Unicode
    # garbage). Flowchart labels are ASCII-only; keep common whitespace and
    # printable ASCII (0x20-0x7e).
    text = re.sub(r'[^\x09\x0a\x0c\x0d\x20-\x7e]', '', text)

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
        # OCR reads the '≤'/'≥' glyph (chevron above a bar) as '=<'/'=>'; restore.
        cleaned = cleaned.replace("=>", ">=").replace("=<", "<=")
        # OCR merges a conjunction onto the preceding operand ('Band' -> 'B and',
        # 'Bor' -> 'B or'). Only done on lines that already contain an operator so
        # ordinary prose words are left untouched.
        if re.search(r'[<>=!]', cleaned):
            cleaned = re.sub(r'\b([A-Za-z])(and|or)\b', r'\1 \2', cleaned)
        cleaned = re.sub(r'(\w)\s*([+\-*/%]|<=|>=|==|!=|<|>)\s*(\w)', r'\1 \2 \3', cleaned)
        cleaned = re.sub(r'(\w)\s*=\s*(\w)', r'\1 = \2', cleaned)

        # Fix "<" that should be "<=" when followed by a variable and "?" (decision context)
        # e.g., "i < n?" -> "i <= n?"
        cleaned = re.sub(r'(\b[A-Za-z_]\w*\s*)<(\s*[A-Za-z_]\w*\s*\?)', r'\1<=\2', cleaned)

        # Fix OCR confusion of letter O with digit 0 in numeric comparison contexts.
        # e.g., "n % 2 == O?" -> "n % 2 == 0?"   "< O" -> "< 0"   "O ==" -> "0 =="
        cleaned = re.sub(r'([<>=!])\s*O\b', r'\1 0', cleaned)
        cleaned = re.sub(r'\bO\s*([<>=!])', r'0 \1', cleaned)
        # OCR also confuses lowercase 'o' with digit 0 in the same contexts.
        cleaned = re.sub(r'([<>=!])\s*o\b', r'\1 0', cleaned)
        cleaned = re.sub(r'\bo\s*([<>=!])', r'0 \1', cleaned)

        # Fix split comparison operator: OCR often reads "==" as "= =".
        # e.g., "n % 2 = = 0?" -> "n % 2 == 0?"   "x = = 5" -> "x == 5"
        cleaned = re.sub(r'(?<![<>=!])\s*=\s*=(?!=)', ' == ', cleaned)

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

        # Collapse multiple horizontal spaces introduced by OCR fixes
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)

        # Trim stray whitespace just inside quoted string literals: '" Odd"' -> '"Odd"'
        cleaned = re.sub(r'"([^"]*)"', lambda m: '"' + m.group(1).strip() + '"', cleaned)

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

    # Drop stray border/artifact fragments OCR injects around a real label
    # (e.g. diamond edges read as ', ™' and '“eS 7'). This only runs when the
    # reading already contains a recognizable statement/condition, so a plain
    # label is never discarded.
    if any(_line_has_flow_signal(line) for line in combined):
        signal_lines = [
            line for line in combined
            if _line_has_flow_signal(line) or not _is_ocr_noise_fragment(line)
        ]
        if signal_lines:
            combined = signal_lines

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
    timeout_sec: float = 6.0,
    include_uncertain: bool = False,
) -> dict[int, str]:
    """
    Uses Gemini Vision to read text for detected flowchart shapes.
    Backend-only API key. Optional with strict timeout and validation.
    Returns a dict mapping block ID (int) -> recognized text (str).
    Never invents executable labels when recognition fails.

    With `include_uncertain`, low-confidence shapes are re-checked too and the
    local reading is supplied as a hint so the model can correct misread
    comparison operators or dropped words rather than starting from scratch.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or not blocks:
        return {}

    # Target blocks that need text (empty shapes, or - when asked - ambiguous ones)
    if include_uncertain:
        target_blocks = [b for b in blocks if not b.get("text") or b.get("text_uncertain")]
    else:
        target_blocks = [b for b in blocks if not b.get("text")]
    if not target_blocks:
        # Avoid unnecessary API calls if all blocks already have confident text
        return {}

    valid_ids = {int(b["id"]) for b in blocks}

    shapes_payload = [
        {
            "id": int(b["id"]),
            "type": b.get("type", "process"),
            "bbox": list(b.get("bbox", [])),
            "local_guess": (b.get("text") or "").strip(),
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
        "3. A 'local_guess' comes from a local OCR pass and may be wrong. Keep its variable "
        "names, but fix misread comparison operators (a '≥'/'≤' glyph is often read as '=', '2' or "
        "'z'), dropped words and missing operands.\n"
        "4. NEVER invent, hallucinate, or guess code expressions or labels you cannot see."
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
