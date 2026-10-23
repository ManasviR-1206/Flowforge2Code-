import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
from tests.test_stage2_image_upload import build_synthetic_factorial_image
import cv_engine

bgr = build_synthetic_factorial_image()
blocks, thresh = cv_engine.detect_symbols(bgr)
connections, warnings = cv_engine.detect_connections(thresh, blocks)

for c in connections:
    print(f"Synthetic: {c['from']} -> {c['to']}, conf={c['confidence']}, uncertain={c.get('uncertain')}")
