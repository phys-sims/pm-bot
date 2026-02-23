"""Work-item validation helpers (schema + business rules)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema" / "work_item.schema.json"
_CHILD_REF_PATTERN = re.compile(r"^(#\d+|https?://[^\s]+/issues/\d+)$")


def load_work_item_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text())


def _schema_errors(work_item: dict[str, Any], schema: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    required = schema.get("required", [])
    properties = schema.get("properties", {})

    for key in sorted(required):
        if key not in work_item:
            errors.append(
                {
                    "code": "SCHEMA_REQUIRED",
                    "path": f"$.{key}",
                    "message": f"'{key}' is a required property",
                }
            )

    for key, value in sorted(work_item.items()):
        prop_schema = properties.get(key)
        if not prop_schema:
            continue

        expected_type = prop_schema.get("type")
        if expected_type == "string" and not isinstance(value, str):
            errors.append(
                {
                    "code": "SCHEMA_TYPE",
                    "path": f"$.{key}",
                    "message": f"{value!r} is not of type 'string'",
                }
            )
            continue
        if expected_type == "number" and not isinstance(value, (int, float)):
            errors.append(
                {
                    "code": "SCHEMA_TYPE",
                    "path": f"$.{key}",
                    "message": f"{value!r} is not of type 'number'",
                }
            )
            continue

        if "enum" in prop_schema and value not in prop_schema["enum"]:
            errors.append(
                {
                    "code": "SCHEMA_ENUM",
                    "path": f"$.{key}",
                    "message": f"{value!r} is not one of {prop_schema['enum']}",
                }
            )

        if (
            "minimum" in prop_schema
            and isinstance(value, (int, float))
            and value < prop_schema["minimum"]
        ):
            errors.append(
                {
                    "code": "SCHEMA_MINIMUM",
                    "path": f"$.{key}",
                    "message": f"{value} is less than the minimum of {prop_schema['minimum']}",
                }
            )

    return errors


def validate_work_item(
    work_item: dict[str, Any],
    *,
    required_headings: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return deterministic machine-readable validation errors."""
    errors: list[dict[str, Any]] = []

    schema = load_work_item_schema()
    errors.extend(_schema_errors(work_item, schema))

    for heading in sorted(required_headings or []):
        errors.append(
            {
                "code": "RULE_REQUIRED_HEADING_EMPTY",
                "path": f"$.fields[{heading}]",
                "message": f"Missing required heading content: {heading}",
            }
        )

    refs = work_item.get("relationships", {}).get("children_refs", [])
    for idx, ref in enumerate(refs):
        if not isinstance(ref, str) or not _CHILD_REF_PATTERN.match(ref.strip()):
            errors.append(
                {
                    "code": "RULE_CHILD_REF_INVALID",
                    "path": f"$.relationships.children_refs[{idx}]",
                    "message": "Child reference must be an issue number (#123) or issue URL (.../issues/<number>).",
                }
            )

    if work_item.get("type") == "task":
        parent_feature = str(work_item.get("fields", {}).get("Parent Feature URL", "")).strip()
        if not parent_feature:
            errors.append(
                {
                    "code": "RULE_TASK_PARENT_FEATURE_URL_REQUIRED",
                    "path": "$.fields[Parent Feature URL]",
                    "message": "Task items require a non-empty 'Parent Feature URL' heading.",
                }
            )

    return sorted(errors, key=lambda e: (e["code"], e["path"], e["message"]))
