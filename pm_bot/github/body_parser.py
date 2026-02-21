"""Markdown heading parser (scaffold).

Your existing workflow parses issue bodies by headings like:
- Area
- Priority
- Size
- Estimate (hrs)
- Risk
- Blocked by
- Actual (hrs)

Agents should implement a deterministic parser + renderer that matches GitHub issue form output.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Dict, Optional

HEADING_RE = re.compile(r"^#{2,6}\s+(.+?)\s*$")

@dataclass
class ParsedHeadings:
    headings: Dict[str, str]

def parse_headings(markdown: str) -> ParsedHeadings:
    """Parse `### Heading` blocks into {Heading: value_text}.

    Naive scaffold:
    - considers any markdown heading line
    - value is the contiguous non-heading block until next heading
    """
    lines = markdown.splitlines()
    out: Dict[str, list[str]] = {}
    current: Optional[str] = None
    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            current = m.group(1).strip()
            out.setdefault(current, [])
            continue
        if current is not None:
            out[current].append(line)

    normalized = {k: "\n".join(v).strip() for k, v in out.items()}
    return ParsedHeadings(headings=normalized)
