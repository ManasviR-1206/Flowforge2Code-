import re

def clean_leading_trailing(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r'^[:;.,|/\\~`_jJ!?-]+\s+(?=(?:Input|Print|Start|End|[A-Za-z_]\w*\s*=))', '', cleaned)
    cleaned = re.sub(r'^[(\[{]\s*(?=(?:Input|Print|Start|End|[A-Za-z_]\w*\s*=))', '', cleaned)
    cleaned = re.sub(r'\s+[*+~`]+$', '', cleaned)
    return cleaned.strip()

tests = [
    ": Input n",
    "j Print fact",
    "i Start *",
    "(end",
    "Start",
    "End",
    "fact = 1",
]
for t in tests:
    print(repr(t), "->", repr(clean_leading_trailing(t)))
