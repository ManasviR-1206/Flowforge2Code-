import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import ocr_engine

surround = cv2.imread("scratch/surround.png")
for psm in (6, 11):
    d = ocr_engine.pytesseract.image_to_data(surround, config=f"--psm {psm}", output_type=ocr_engine.pytesseract.Output.DICT)
    print(f"\n--- PSM {psm} ---")
    for i, t in enumerate(d["text"]):
        if t.strip():
            print(f"word: {repr(t)}, conf={d['conf'][i]}, box=({d['left'][i]}, {d['top'][i]}, {d['width'][i]}, {d['height'][i]})")
