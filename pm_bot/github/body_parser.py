"""Markdown heading and checklist parsing helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict

HEADING_RE = re.compile(r"^#{2,6}\s+(.+?)\s*$")
CHILD_REF_RE = re.compile(r"-\s*\[[ xX]\]\s*(#\d+|https?://\S+)")
NO_RESPONSE_VALUES = {"_No response_", "No response", "N/A", ""}


@dataclass
class ParsedHeadings:
    headings: Dict[str, str]


def parse_headings(markdown: str) -> ParsedHeadings:
    """Parse markdown headings into a map of heading -> body text."""
    lines = markdown.splitlines()
    out: Dict[str, list[str]] = {}
    current: str | None = None

    for line in lines:
        match = HEADING_RE.match(line)
        if match:
            current = match.group(1).strip()
            out.setdefault(current, [])
            continue
        if current is not None:
            out[current].append(line)

    normalized: Dict[str, str] = {}
    for key, values in out.items():
        value = "\n".join(values).strip()
        normalized[key] = "" if value in NO_RESPONSE_VALUES else value

    return ParsedHeadings(headings=normalized)


def parse_child_refs(text: str) -> list[str]:
    """Parse checklist issue references from markdown text."""
    refs = [match.group(1) for match in CHILD_REF_RE.finditer(text)]
    deduped = list(dict.fromkeys(refs))
    return deduped
