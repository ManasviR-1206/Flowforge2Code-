import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
from PIL import Image
import cv_engine
import ocr_engine

img_path = r"C:\Users\Manasvi R\Downloads\Factorial Flowchart_ Input, Loop, Output.png"
pil_img = Image.open(img_path).convert("RGB")
img = cv_engine.normalize_image(pil_img)

# Block 4 is at bbox=(366, 663, 284, 195)
x, y, w, h = 366, 663, 284, 195
crop4 = img[y:y+h, x:x+w]

# Let's test inner region of decision diamond:
# Decision diamond center is (142, 97) inside the crop
# Text is right in the center
ih, iw = crop4.shape[:2]
inner4 = crop4[int(ih*0.3):int(ih*0.7), int(iw*0.25):int(iw*0.75)]
cv2.imwrite("scratch/inner4.png", inner4)

for scale in (1.0, 2.0, 3.0, 4.0):
    sc = cv2.resize(inner4, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(sc, cv2.COLOR_BGR2GRAY)
    for psm in (6, 7, 8, 11, 13):
        txt = ocr_engine.pytesseract.image_to_string(gray, config=f"--psm {psm}").strip()
        if txt:
            print(f"Scale {scale} PSM {psm}: {repr(txt)}")

# Let's also check thresholded versions
gray_inner = cv2.cvtColor(inner4, cv2.COLOR_BGR2GRAY)
for thresh_type in ["otsu", "adaptive", "binary180", "binary200"]:
    if thresh_type == "otsu":
        _, b = cv2.threshold(gray_inner, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif thresh_type == "adaptive":
        b = cv2.adaptiveThreshold(gray_inner, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 4)
    elif thresh_type == "binary180":
        _, b = cv2.threshold(gray_inner, 180, 255, cv2.THRESH_BINARY)
    elif thresh_type == "binary200":
        _, b = cv2.threshold(gray_inner, 200, 255, cv2.THRESH_BINARY)
    
    b_scaled = cv2.resize(b, (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    for psm in (6, 7, 8, 11):
        txt = ocr_engine.pytesseract.image_to_string(b_scaled, config=f"--psm {psm}").strip()
        if txt:
            print(f"Thresh {thresh_type} PSM {psm}: {repr(txt)}")
