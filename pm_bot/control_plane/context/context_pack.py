"""Deterministic context-pack assembly with schema-versioned envelopes."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from pm_bot.control_plane.db.db import OrchestratorDB

SCHEMA_VERSION_V1 = "context_pack/v1"
SCHEMA_VERSION_V2 = "context_pack/v2"

_REASON_BUDGET_EXCEEDED = "budget_exceeded"
_REASON_REDACTION = "redacted_sensitive_value"
_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "api_key",
        re.compile(r"\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+", re.IGNORECASE),
    ),
    (
        "github_pat",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    ),
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def map_v1_to_v2(v1_payload: dict[str, Any]) -> dict[str, Any]:
    """Compatibility mapper for legacy context-pack payloads."""

    content = dict(v1_payload.get("content") or {})
    issue_ref = str(content.get("issue_ref") or "")
    return {
        "schema_version": SCHEMA_VERSION_V2,
        "profile": str(content.get("profile") or "pm-drafting"),
        "root": {"issue_ref": issue_ref},
        "budget": {
            "max_chars": int(v1_payload.get("char_budget") or 0),
            "used_chars": len(_canonical_json(content)),
            "strategy": "truncate_tail",
        },
        "sections": [
            {
                "segment_id": "root.v1-content",
                "kind": "work_item",
                "provenance": "root",
                "title": str(content.get("title") or issue_ref or "root"),
                "source": {"issue_ref": issue_ref},
                "content": _canonical_json(content),
                "char_count": len(_canonical_json(content)),
                "rank": [0, issue_ref],
                "redactions": [],
            }
        ],
        "manifest": {
            "included_segments": ["root.v1-content"],
            "excluded_segments": [],
            "exclusion_reasons": {},
            "redaction_counts": {"total": 0, "categories": {}},
            "provenance": [{"segment_id": "root.v1-content", "source_issue_ref": issue_ref}],
        },
        "hash": str(v1_payload.get("hash") or _stable_hash(content)),
        "content": content,
    }


def _redact_content(text: str) -> tuple[str, list[dict[str, str]]]:
    redactions: list[dict[str, str]] = []
    redacted_text = text
    for category, pattern in _SECRET_PATTERNS:
        matches = list(pattern.finditer(redacted_text))
        if not matches:
            continue
        redacted_text = pattern.sub("[REDACTED]", redacted_text)
        redactions.append(
            {
                "category": category,
                "reason_code": _REASON_REDACTION,
                "count": len(matches),
            }
        )
    return redacted_text, redactions


def _segment_candidates(db: OrchestratorDB, issue_ref: str, profile: str) -> list[dict[str, Any]]:
    item = db.get_work_item(issue_ref)
    if item is None:
        raise ValueError(f"Unknown work item: {issue_ref}")

    related = db.get_related(issue_ref)
    candidates: list[dict[str, Any]] = [
        {
            "segment_id": "root.instructions",
            "kind": "instructions",
            "title": "Agent instructions",
            "provenance": "profile",
            "source": {"kind": "builtin", "profile": profile},
            "payload": {
                "profile": profile,
                "guidance": "Use deterministic edits and preserve approval gates.",
            },
            "rank": (0, "root.instructions"),
        },
        {
            "segment_id": "root.work_item",
            "kind": "work_item",
            "title": str(item.get("title") or issue_ref),
            "provenance": "root",
            "source": {"issue_ref": issue_ref},
            "payload": {
                "issue_ref": issue_ref,
                "title": item.get("title", ""),
                "type": item.get("type", ""),
                "fields": item.get("fields", {}),
                "relationships": related,
            },
            "rank": (1, issue_ref),
        },
    ]

    for idx, parent_ref in enumerate(sorted(related.get("parents", []))):
        parent = db.get_work_item(parent_ref)
        if parent is None:
            continue
        candidates.append(
            {
                "segment_id": f"parent.{idx}",
                "kind": "related_work_item",
                "title": str(parent.get("title") or parent_ref),
                "provenance": "parent",
                "source": {"issue_ref": parent_ref},
                "payload": parent,
                "rank": (2, parent_ref),
            }
        )

    for idx, child_ref in enumerate(sorted(related.get("children", []))):
        child = db.get_work_item(child_ref)
        if child is None:
            continue
        candidates.append(
            {
                "segment_id": f"child.{idx}",
                "kind": "related_work_item",
                "title": str(child.get("title") or child_ref),
                "provenance": "child",
                "source": {"issue_ref": child_ref},
                "payload": child,
                "rank": (3, child_ref),
            }
        )

    return sorted(candidates, key=lambda c: (c["rank"][0], c["rank"][1]))


def build_context_pack(
    db: OrchestratorDB,
    issue_ref: str,
    profile: str = "pm-drafting",
    char_budget: int = 4000,
    schema_version: str = SCHEMA_VERSION_V2,
) -> dict[str, Any]:
    if char_budget <= 0:
        raise ValueError("char_budget must be positive")

    if schema_version == SCHEMA_VERSION_V1:
        item = db.get_work_item(issue_ref)
        if item is None:
            raise ValueError(f"Unknown work item: {issue_ref}")
        canonical = {
            "profile": profile,
            "issue_ref": issue_ref,
            "title": item.get("title", ""),
            "type": item.get("type", ""),
            "fields": item.get("fields", {}),
            "relationships": db.get_related(issue_ref),
        }
        serialized = json.dumps(canonical, sort_keys=True)
        if len(serialized) > char_budget:
            serialized = serialized[:char_budget]
        return {
            "schema_version": SCHEMA_VERSION_V1,
            "hash": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
            "content": json.loads(serialized),
            "char_budget": char_budget,
        }

    if schema_version != SCHEMA_VERSION_V2:
        raise ValueError("Unsupported context pack schema_version")

    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    provenance: list[dict[str, str]] = []
    reason_counts: dict[str, int] = {}
    redaction_categories: dict[str, int] = {}
    used_chars = 0

    for candidate in _segment_candidates(db=db, issue_ref=issue_ref, profile=profile):
        redacted_text, redactions = _redact_content(_canonical_json(candidate["payload"]))
        segment = {
            "segment_id": candidate["segment_id"],
            "kind": candidate["kind"],
            "provenance": candidate["provenance"],
            "title": candidate["title"],
            "source": candidate["source"],
            "content": redacted_text,
            "char_count": len(redacted_text),
            "rank": [candidate["rank"][0], candidate["rank"][1]],
            "redactions": redactions,
        }
        if used_chars + segment["char_count"] > char_budget:
            excluded.append(
                {
                    "segment_id": candidate["segment_id"],
                    "reason_code": _REASON_BUDGET_EXCEEDED,
                    "char_count": segment["char_count"],
                    "rank": [candidate["rank"][0], candidate["rank"][1]],
                }
            )
            reason_counts[_REASON_BUDGET_EXCEEDED] = (
                reason_counts.get(_REASON_BUDGET_EXCEEDED, 0) + 1
            )
            continue

        included.append(segment)
        used_chars += segment["char_count"]
        provenance.append(
            {
                "segment_id": candidate["segment_id"],
                "source_issue_ref": str(candidate["source"].get("issue_ref") or issue_ref),
            }
        )
        for redaction in redactions:
            category = redaction["category"]
            redaction_categories[category] = redaction_categories.get(category, 0) + int(
                redaction["count"]
            )

    payload_without_hash = {
        "schema_version": SCHEMA_VERSION_V2,
        "profile": profile,
        "root": {"issue_ref": issue_ref},
        "budget": {
            "max_chars": char_budget,
            "used_chars": used_chars,
            "strategy": "drop_low_priority",
        },
        "sections": included,
        "manifest": {
            "included_segments": [segment["segment_id"] for segment in included],
            "excluded_segments": excluded,
            "exclusion_reasons": reason_counts,
            "redaction_counts": {
                "total": sum(redaction_categories.values()),
                "categories": redaction_categories,
            },
            "provenance": provenance,
        },
    }

    output = dict(payload_without_hash)
    output["hash"] = _stable_hash(payload_without_hash)
    root_segment = next(
        (segment for segment in included if segment["segment_id"] == "root.work_item"),
        None,
    )
    if root_segment is not None:
        output["content"] = json.loads(root_segment["content"])
    elif included:
        output["content"] = json.loads(included[0]["content"])
    else:
        output["content"] = {}
    return output
