"""Convert v2 layout markers to readable text, retaining table HTML and content."""
from __future__ import annotations

import re

# Only remove a complete, recognized layout header. Unknown/malformed output
# remains visible instead of silently deleting potentially recognized text.
_COORD = r"-?\d+(?:\.\d+)?"
_BOX = rf"\[\s*{_COORD}(?:\s*[,，]\s*{_COORD}){{3}}\s*\]"
BLOCK_HEADER = re.compile(
    rf"<BLOCK>\s*([a-zA-Z_][a-zA-Z_0-9-]*)\s*"
    rf"(?:<LEVEL\d+>\s*)?(?:{_BOX}\s*)?(?:<LEVEL\d+>\s*)?<FORK>"
)


def readable_ocr2_text(value: str) -> str:
    text = value.replace("\x00", "").replace("<｜end▁of▁sentence｜>", "")
    # Preserve all block bodies, including figures, footnotes, headers and tables.
    text = BLOCK_HEADER.sub("\n\n", text)
    text = text.replace("<PAGE>", "\n\n").replace("<MERGE>", "\n")
    return text.strip()
