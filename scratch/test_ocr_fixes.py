"""Test OCR cleaning fixes for factorial flowchart issues."""
from ocr_engine import clean_ocr_text

# Test 1: Spurious decimal point fix
assert clean_ocr_text('fact = 1.1') == 'fact = 1', f"Got: {clean_ocr_text('fact = 1.1')}"
assert clean_ocr_text('i = 1.1') == 'i = 1', f"Got: {clean_ocr_text('i = 1.1')}"
assert clean_ocr_text('x = 2.0') == 'x = 2', f"Got: {clean_ocr_text('x = 2.0')}"

# Test 2: <= misread as < fix
assert clean_ocr_text('i <= n?') == 'i <= n?', f"Got: {clean_ocr_text('i <= n?')}"
# Should NOT change already-correct <=
assert clean_ocr_text('i <= n') == 'i <= n', f"Got: {clean_ocr_text('i <= n')}"

# Test 3: Normal text should not be affected
assert clean_ocr_text('fact = fact * i') == 'fact = fact * i', f"Got: {clean_ocr_text('fact = fact * i')}"
assert clean_ocr_text('i = i + 1') == 'i = i + 1', f"Got: {clean_ocr_text('i = i + 1')}"

print('All OCR cleaning tests passed!')
