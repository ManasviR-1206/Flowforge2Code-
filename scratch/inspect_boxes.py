import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
import ocr_engine

inner4 = cv2.imread("scratch/inner4.png")
d = ocr_engine.pytesseract.image_to_boxes(inner4)
print("Boxes in inner4:\n" + d)
