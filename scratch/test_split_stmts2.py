import re

def split_multistatements(text: str) -> str:
    pattern = r'(\b\d+|\b[A-Za-z_]\w*)\s+([A-Za-z_]\w*\s*(?:=|\+=|-=|\*=|/=|%=)(?!=))'
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
