"""Parse issue markdown into canonical WorkItem JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pm_bot.github.body_parser import parse_child_refs, parse_headings

PROJECT_FIELDS = {
    "Area": "area",
    "Priority": "priority",
    "Size": "size",
    "Size (Epic)": "size",
    "Estimate (hrs)": "estimate_hrs",
    "Actual (hrs)": "actual_hrs",
    "Risk": "risk",
    "Blocked by": "blocked_by",
}
CHILD_HEADINGS = {
    "Child tasks",
    "Child Issues (link Features/Tasks/Tests/Benches/Docs)",
}


def _to_number_if_possible(value: str) -> float | str:
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def load_template_map() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "schema" / "template_map.json"
    return json.loads(path.read_text())


def parse_issue_body(markdown: str, item_type: str, title: str = "") -> dict[str, Any]:
    parsed = parse_headings(markdown)
    template_map = load_template_map()
    if item_type not in template_map:
        raise ValueError(f"Unknown issue type: {item_type}")

    work_item: dict[str, Any] = {
        "title": title,
        "type": item_type,
        "fields": {},
        "relationships": {"children_refs": []},
    }

    for heading, value in parsed.headings.items():
        if heading in PROJECT_FIELDS:
            mapped = PROJECT_FIELDS[heading]
            work_item[mapped] = _to_number_if_possible(value)
        else:
            work_item["fields"][heading] = value

        if heading in CHILD_HEADINGS:
            refs = parse_child_refs(value)
            work_item.setdefault("relationships", {}).setdefault("children_refs", []).extend(
                refs
            )

    work_item["relationships"]["children_refs"] = list(
        dict.fromkeys(work_item["relationships"]["children_refs"])
    )

    missing = []
    for required_heading in template_map[item_type]["required_headings"]:
        raw_value = parsed.headings.get(required_heading, "").strip()
        if not raw_value:
            missing.append(required_heading)
    if missing:
        work_item["validation_errors"] = [
            f"Missing required heading content: {name}" for name in missing
        ]

    return work_item
