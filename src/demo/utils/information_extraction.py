from __future__ import annotations

import re

def extract_title(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return "untitled_story"

    # 1. Look for explicit Title label with optional punctuation
    label_pattern = re.compile(
        r'(?i)^(?:[\-\*\#\>\s\d\.]*)'         # optional prefixes: -, *, #, numbers, etc.
        r'(?:\*{0,2}title\*{0,2}|title)'      # title label
        r'\s*(?:[:\-–—]\s*|\s+)?'             # optional separator or just whitespace
        r'(.+)?$'                             # capture title if present
    )

    for i, line in enumerate(lines):
        m = label_pattern.match(line)
        if m:
            title = m.group(1)
            if title:               # Title is on same line
                return clean_title(title)
            # Title is on the *next* line
            if i + 1 < len(lines):
                return clean_title(lines[i+1])

    # 2. If a markdown header exists, use it
    header_pattern = re.compile(r'^\s*#{1,6}\s*(.+)$')
    for line in lines:
        m = header_pattern.match(line)
        if m:
            return clean_title(m.group(1))

    # 3. Fallback: first meaningful line
    return clean_title(lines[0])


def clean_title(title: str) -> str:
    # Remove surrounding markdown or punctuation decorations
    title = re.sub(r'^[#\-\*\>\s\"\']+', '', title)
    title = re.sub(r'[#\-\*\>\s\"\']+$', '', title)
    return title.strip()