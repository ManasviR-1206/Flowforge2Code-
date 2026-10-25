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

# In the image:
# Yes is at (269, 714), width 55, height 27
# No is at (700, 716), width 46, height 28
box_yes = (269, 714, 55, 27)
box_no = (700, 716, 46, 28)

print("Direct box Yes:", ocr_engine.extract_region_text_with_confidence(img, box_yes))
print("Direct box No:", ocr_engine.extract_region_text_with_confidence(img, box_no))

# Now let's see what points_to_check in api_server was testing!
b4 = {"bbox": (366, 663, 284, 195), "center": (508, 760)}
# Connection 4 -> 5: vector=((357, 757), (213, 880))
# Connection 4 -> 6: vector=((659, 759), (816, 887))
bx, by, bw, bh = b4["bbox"]
cx, cy = b4["center"]

# For conn 4 -> 5 (tcx < cx):
lx, ly = bx, by + bh // 2 # (366, 760)
print("lx, ly:", lx, ly)
# points tested: (lx - 45, ly - 30) = (321, 730)
# (lx - 45, ly + 15) = (321, 775)
# (lx - 30, ly - 35) = (336, 725)
# (lx - 60, ly - 20) = (306, 740)
# But Yes is at x=269, y=714!
# 306 - 40 = 266, 740 - 24 = 716!
for px, py in [(321, 730), (321, 775), (336, 725), (306, 740), (290, 720)]:
    w_box, h_box = 80, 48
    box = (px - w_box // 2, py - h_box // 2, w_box, h_box)
    res = ocr_engine.extract_region_text_with_confidence(img, box)
    print(f"Test at ({px}, {py}): {res}")
