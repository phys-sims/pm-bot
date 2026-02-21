"""Render canonical WorkItem JSON into deterministic markdown."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIELD_TO_HEADING = {
    "area": "Area",
    "priority": "Priority",
    "size": "Size",
    "estimate_hrs": "Estimate (hrs)",
    "actual_hrs": "Actual (hrs)",
    "risk": "Risk",
    "blocked_by": "Blocked by",
}


def load_template_map() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "schema" / "template_map.json"
    return json.loads(path.read_text())


def _value_for_heading(item: dict[str, Any], heading: str) -> str:
    fields = item.get("fields", {})
    if heading in fields:
        return str(fields[heading]).strip()

    for key, mapped_heading in FIELD_TO_HEADING.items():
        if mapped_heading == heading and item.get(key) not in (None, ""):
            return str(item[key]).strip()

    if heading == "Child tasks":
        refs = item.get("relationships", {}).get("children_refs", [])
        if refs:
            return "\n".join(f"- [ ] {ref}" for ref in refs)
        return "- [ ] #<issue-number-1>"

    if heading == "Child Issues (link Features/Tasks/Tests/Benches/Docs)":
        refs = item.get("relationships", {}).get("children_refs", [])
        if refs:
            return "\n".join(f"- [ ] {ref}" for ref in refs)
        return "- [ ] #<issue>"

    return "_No response_"


def render_issue_body(item: dict[str, Any]) -> str:
    item_type = item["type"]
    template_map = load_template_map()
    if item_type not in template_map:
        raise ValueError(f"Unknown issue type: {item_type}")

    headings = template_map[item_type]["headings"]
    chunks = []
    for heading in headings:
        value = _value_for_heading(item, heading)
        chunks.append(f"### {heading}\n{value}".strip())

    return "\n\n".join(chunks).strip() + "\n"
