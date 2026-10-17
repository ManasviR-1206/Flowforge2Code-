import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
import ocr_engine

def check_underline_under_operator(roi, box_tuple):
    if len(roi.shape) == 3:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    else:
        gray = roi
    h, w = gray.shape[:2]
    char, l, b_tess, r, t_tess = box_tuple
    top = h - t_tess
    bot = h - b_tess
    char_h = bot - top
    char_w = r - l
    check_y1 = bot
    check_y2 = min(h, bot + int(char_h * 0.8) + 5)
    check_x1 = max(0, l - 3)
    check_x2 = min(w, r + 3)
    below_crop = gray[check_y1:check_y2, check_x1:check_x2]
    if below_crop.size == 0:
        return False
    _, bin_below = cv2.threshold(below_crop, 180, 255, cv2.THRESH_BINARY_INV)
    row_ink = np.sum(bin_below > 0, axis=1)
    has_line = any(cnt >= char_w * 0.5 for cnt in row_ink)
    return has_line

inner4 = cv2.imread(r"c:\Users\Manasvi R\OneDrive\Desktop\FlowForge2Code\scratch\inner4.png")
boxes = ocr_engine.pytesseract.image_to_boxes(inner4).strip().splitlines()
for line in boxes:
    parts = line.split()
    char = parts[0]
    box = (char, int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]))
    if char in ("<", ">"):
        has_ul = check_underline_under_operator(inner4, box)
        print(f"Char '{char}': has_underline={has_ul}")
