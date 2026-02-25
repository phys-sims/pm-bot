"""Natural-text intake and deterministic ReportIR preview helpers."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "item"


def _iter_natural_text_items(natural_text: str) -> list[str]:
    lines = [line.strip() for line in natural_text.splitlines() if line.strip()]
    bullet_lines = [
        line[1:].strip() for line in lines if line.startswith("-") or line.startswith("*")
    ]
    if bullet_lines:
        return bullet_lines
    return lines


def draft_report_ir_from_natural_text(
    *,
    natural_text: str,
    org: str,
    repos: list[str],
    generated_at: str = "",
) -> dict[str, Any]:
    items = _iter_natural_text_items(natural_text)
    if not items:
        items = ["Triage natural-text plan"]

    title = items[0]
    features: list[dict[str, Any]] = []
    for index, text in enumerate(items, start=1):
        stable_id = f"feat:{_slugify(text)}"
        if any(feature["stable_id"] == stable_id for feature in features):
            stable_id = f"{stable_id}-{index}"
        features.append(
            {
                "stable_id": stable_id,
                "title": text,
                "goal": text,
                "area": "triage",
                "priority": "Triage",
            }
        )

    resolved_generated_at = generated_at.strip() or datetime.now(timezone.utc).date().isoformat()
    return {
        "schema_version": "report_ir/v1",
        "report": {
            "title": title,
            "generated_at": resolved_generated_at,
            "scope": {
                "org": org.strip(),
                "repos": [repo.strip() for repo in repos if repo.strip()],
            },
            "source": {
                "kind": "llm_stub",
                "prompt_hash": hashlib.sha256(natural_text.encode("utf-8")).hexdigest()[:16],
            },
        },
        "features": features,
    }


def validate_report_ir(report_ir: dict[str, Any]) -> dict[str, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if report_ir.get("schema_version") != "report_ir/v1":
        errors.append("schema_version must equal report_ir/v1")

    report = report_ir.get("report")
    if not isinstance(report, dict):
        errors.append("report must be an object")
        report = {}

    if not str(report.get("title", "")).strip():
        errors.append("report.title is required")
    scope = report.get("scope") if isinstance(report.get("scope"), dict) else {}
    if not str(scope.get("org", "")).strip():
        errors.append("report.scope.org is required")

    all_items: list[dict[str, Any]] = []
    for collection_name in ("epics", "features", "tasks"):
        collection = report_ir.get(collection_name) or []
        if not isinstance(collection, list):
            errors.append(f"{collection_name} must be a list")
            continue
        for item in collection:
            if isinstance(item, dict):
                all_items.append(item)

    stable_ids: list[str] = []
    for item in all_items:
        stable_id = str(item.get("stable_id", "")).strip()
        if not stable_id:
            errors.append("stable_id is required for all work items")
            continue
        stable_ids.append(stable_id)
        if not str(item.get("title", "")).strip():
            errors.append(f"title is required for {stable_id}")
        if not str(item.get("area", "")).strip():
            warnings.append(f"{stable_id} missing area; triage default expected")
        if not str(item.get("priority", "")).strip():
            warnings.append(f"{stable_id} missing priority; triage default expected")

    duplicates = sorted({stable_id for stable_id in stable_ids if stable_ids.count(stable_id) > 1})
    for duplicate in duplicates:
        errors.append(f"stable_id duplicated: {duplicate}")

    known_ids = set(stable_ids)
    for feature in report_ir.get("features") or []:
        epic_id = str((feature or {}).get("epic_id", "")).strip()
        if epic_id and epic_id not in known_ids:
            errors.append(f"feature epic_id not found: {epic_id}")
    for task in report_ir.get("tasks") or []:
        feature_id = str((task or {}).get("feature_id", "")).strip()
        if feature_id and feature_id not in known_ids:
            errors.append(f"task feature_id not found: {feature_id}")

    return {"errors": sorted(set(errors)), "warnings": sorted(set(warnings))}


def build_changeset_preview(report_ir: dict[str, Any]) -> dict[str, Any]:
    report = report_ir.get("report") if isinstance(report_ir.get("report"), dict) else {}
    scope = report.get("scope") if isinstance(report.get("scope"), dict) else {}
    scope_repos = [str(repo).strip() for repo in (scope.get("repos") or []) if str(repo).strip()]
    org = str(scope.get("org", "")).strip()
    fallback_repo = f"{org}/pm-bot" if org else ""

    entries: list[dict[str, Any]] = []
    for item_type in ("epics", "features", "tasks"):
        for item in report_ir.get(item_type) or []:
            if not isinstance(item, dict):
                continue
            stable_id = str(item.get("stable_id", "")).strip()
            title = str(item.get("title", "")).strip()
            if not stable_id or not title:
                continue
            repo_hint = str(item.get("repo", "")).strip()
            repo = repo_hint or (scope_repos[0] if scope_repos else fallback_repo)
            if not repo:
                continue
            payload = {
                "issue_ref": "",
                "title": title,
                "body_fields": {
                    "Area": str(item.get("area", "triage") or "triage"),
                    "Priority": str(item.get("priority", "Triage") or "Triage"),
                    "Size": str(item.get("size", "") or ""),
                    "Estimate (hrs)": item.get("estimate_hrs", ""),
                    "Risk": str(item.get("risk", "") or ""),
                    "Blocked by": ", ".join(item.get("blocked_by") or []),
                    "Actual (hrs)": "",
                },
            }
            idempotency_key = f"report_ir:{repo}:{stable_id}:{hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()[:12]}"
            entries.append(
                {
                    "repo": repo,
                    "operation": "create_issue",
                    "stable_id": stable_id,
                    "target_ref": "",
                    "payload": payload,
                    "idempotency_key": idempotency_key,
                }
            )

    entries.sort(key=lambda row: (row["repo"], row["stable_id"], row["operation"]))
    repos = sorted({entry["repo"] for entry in entries})
    return {
        "schema_version": "changeset_preview/v1",
        "items": entries,
        "summary": {
            "count": len(entries),
            "repos": repos,
            "repo_count": len(repos),
        },
    }
