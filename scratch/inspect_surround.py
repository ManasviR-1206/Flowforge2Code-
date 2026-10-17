import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
from PIL import Image
import cv_engine
import ocr_engine

img_path = r"C:\Users\Manasvi R\Downloads\Factorial Flowchart_ Input, Loop, Output.png"
pil_img = Image.open(img_path).convert("RGB")
img = cv_engine.normalize_image(pil_img)

# Let's save the surround image
b4_bbox = (366, 663, 284, 195)
x, y, w, h = b4_bbox
surround = img[max(0, y-100):min(img.shape[0], y+h+100), max(0, x-150):min(img.shape[1], x+w+150)]
cv2.imwrite("scratch/surround.png", surround)
print("Saved scratch/surround.png, shape:", surround.shape)

# Let's run image_to_string with different configs on surround
for psm in (3, 6, 11, 12):
    s = ocr_engine.pytesseract.image_to_string(surround, config=f"--psm {psm}")
    print(f"PSM {psm}:\n{repr(s)}")
