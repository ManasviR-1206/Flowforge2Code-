import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np

inner4 = cv2.imread("scratch/inner4.png")
ih, iw = inner4.shape[:2]
# Box is x=34..56, y=26..47 from bottom
# in standard image coords:
# y1 = ih - 47, y2 = ih - 26
y1 = max(0, ih - 55)
y2 = min(ih, ih - 15)
x1 = 30
x2 = 60
crop_symbol = inner4[y1:y2, x1:x2]
cv2.imwrite("scratch/symbol_le.png", crop_symbol)
print(f"Symbol shape: {crop_symbol.shape}")

gray = cv2.cvtColor(crop_symbol, cv2.COLOR_BGR2GRAY)
_, bin_sym = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
print("Binary symbol:\n")
for row in bin_sym:
    print("".join("#" if p > 0 else "." for p in row))
