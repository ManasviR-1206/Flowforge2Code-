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

# Block 3 is at bbox=(334, 421, 347, 140)
x, y, w, h = 334, 421, 347, 140
crop3 = img[y:y+h, x:x+w]
print("Block 3 shape:", crop3.shape)

# Let's save crop3 and see what's in it or test various configs
cv2.imwrite("scratch/crop3.png", crop3)

# Test different PSMs and pre-processing
for psm in (3, 4, 6, 11, 12):
    txt = ocr_engine.pytesseract.image_to_string(crop3, config=f"--psm {psm}")
    print(f"PSM {psm}: {repr(txt.strip())}")

# Let's test grayscale / contrast / thresholding on crop3
gray3 = cv2.cvtColor(crop3, cv2.COLOR_BGR2GRAY)
for thresh_val in (150, 180, 200, 220):
    _, bin_img = cv2.threshold(gray3, thresh_val, 255, cv2.THRESH_BINARY)
    for psm in (6, 11):
        txt = ocr_engine.pytesseract.image_to_string(bin_img, config=f"--psm {psm}")
        if txt.strip():
            print(f"thresh {thresh_val} PSM {psm}: {repr(txt.strip())}")

# Now Block 4 (decision diamond)
x, y, w, h = 366, 663, 284, 195
crop4 = img[y:y+h, x:x+w]
cv2.imwrite("scratch/crop4.png", crop4)
print("\n--- Block 4 (decision) ---")
for psm in (3, 6, 7, 8, 11, 13):
    txt = ocr_engine.pytesseract.image_to_string(crop4, config=f"--psm {psm}")
    print(f"PSM {psm}: {repr(txt.strip())}")

gray4 = cv2.cvtColor(crop4, cv2.COLOR_BGR2GRAY)
for thresh_val in (150, 180, 200, 220):
    _, bin_img = cv2.threshold(gray4, thresh_val, 255, cv2.THRESH_BINARY)
    for psm in (6, 7, 11):
        txt = ocr_engine.pytesseract.image_to_string(bin_img, config=f"--psm {psm}")
        if txt.strip():
            print(f"thresh {thresh_val} PSM {psm}: {repr(txt.strip())}")
