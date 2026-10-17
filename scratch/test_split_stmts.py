import re

def split_multistatements(text: str) -> str:
    # If text has multiple assignments concatenated without newline/semicolon:
    # e.g. "fact = 1 i = 1" or "fact = fact * i i = i + 1"
    # Matches an expression boundary followed by a new assignment target
    pattern = r'(\b\d+|\b[A-Za-z_]\w*)\s+([A-Za-z_]\w*\s*(?:=|\+=|-=|\*=|/=|%=)\s*[^=])'
    # Repeatedly apply in case of 3+ statements
    prev = None
    cur = text
    while prev != cur:
        prev = cur
        cur = re.sub(pattern, r'\1\n\2', cur)
    return cur

tests = [
    "fact = 1 i = 1",
    "fact = fact * i i = i + 1",
    "a = 5 b = 10 c = 20",
    "i = 1",
    "Input n",
    "Print fact",
    "i <= n?",
]

for t in tests:
    print(repr(t), "->", repr(split_multistatements(t)))
