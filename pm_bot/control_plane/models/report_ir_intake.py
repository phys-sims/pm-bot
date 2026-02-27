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


def _extract_tokens(text: str) -> tuple[str, dict[str, Any]]:
    metadata: dict[str, Any] = {}
    cleaned = text

    token_patterns = {
        "area": r"\barea\s*[:=]\s*([a-z0-9_-]+)",
        "priority": r"\bpriority\s*[:=]\s*([a-z0-9_-]+)",
        "estimate_hrs": r"\b(?:estimate|est|hrs|hours)\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)",
    }

    for key, pattern in token_patterns.items():
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if not match:
            continue
        raw_value = match.group(1).strip()
        if key == "estimate_hrs":
            metadata[key] = float(raw_value) if "." in raw_value else int(raw_value)
        else:
            metadata[key] = raw_value
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    return re.sub(r"\s{2,}", " ", cleaned).strip(" -,;"), metadata


def _strip_dependency_phrases(text: str) -> str:
    return re.sub(r"\b(?:depends on|blocked by)\s+[^.;]+", "", text, flags=re.IGNORECASE).strip(
        " -,;"
    )


def _extract_dependency_phrases(text: str) -> dict[str, list[str]]:
    dependencies: dict[str, list[str]] = {"depends_on": [], "blocked_by": []}
    patterns = {
        "depends_on": r"depends on\s+([^.;]+)",
        "blocked_by": r"blocked by\s+([^.;]+)",
    }
    for field, pattern in patterns.items():
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            values = re.split(r",|\band\b", match.group(1), flags=re.IGNORECASE)
            normalized = [value.strip(" #[]()") for value in values if value.strip(" #[]()")]
            dependencies[field].extend(normalized)
    return dependencies


def _stable_id_for(kind: str, text: str, counts: dict[str, int]) -> str:
    base = f"{kind}:{_slugify(text)}"
    seen = counts.get(base, 0)
    counts[base] = seen + 1
    return base if seen == 0 else f"{base}-{seen + 1}"


def _draft_report_ir_from_structured_markdown(
    *,
    natural_text: str,
    org: str,
    repos: list[str],
    generated_at: str = "",
) -> dict[str, Any] | None:
    lines = [line.rstrip() for line in natural_text.splitlines()]
    if not any(line.lstrip().startswith("#") for line in lines):
        return None

    epics: list[dict[str, Any]] = []
    features: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []
    id_counts: dict[str, int] = {}

    current_epic_id = ""
    current_feature_id = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            depth = len(heading.group(1))
            heading_text = heading.group(2).strip()
            normalized = heading_text.lower()
            content, metadata = _extract_tokens(_strip_dependency_phrases(heading_text))

            if "epic" in normalized:
                title = re.sub(r"^epic\s*[:\-]\s*", "", content, flags=re.IGNORECASE).strip()
                stable_id = _stable_id_for("epic", title or content, id_counts)
                current_epic_id = stable_id
                current_feature_id = ""
                epics.append(
                    {
                        "stable_id": stable_id,
                        "title": title or content,
                        "objective": title or content,
                        "area": str(metadata.get("area", "triage")),
                        "priority": str(metadata.get("priority", "Triage")),
                    }
                )
                continue

            if "feature" in normalized:
                title = re.sub(r"^feature\s*[:\-]\s*", "", content, flags=re.IGNORECASE).strip()
                stable_id = _stable_id_for("feat", title or content, id_counts)
                current_feature_id = stable_id
                if depth <= 1:
                    current_epic_id = ""
                feature: dict[str, Any] = {
                    "stable_id": stable_id,
                    "title": title or content,
                    "goal": title or content,
                    "area": str(metadata.get("area", "triage")),
                    "priority": str(metadata.get("priority", "Triage")),
                }
                if current_epic_id:
                    feature["epic_id"] = current_epic_id
                if "estimate_hrs" in metadata:
                    feature["estimate_hrs"] = metadata["estimate_hrs"]
                feature_deps = _extract_dependency_phrases(heading_text)
                if feature_deps["depends_on"]:
                    feature["depends_on"] = feature_deps["depends_on"]
                if feature_deps["blocked_by"]:
                    feature["blocked_by"] = feature_deps["blocked_by"]
                features.append(feature)
                continue

            if "task" in normalized:
                title = re.sub(r"^task\s*[:\-]\s*", "", content, flags=re.IGNORECASE).strip()
                stable_id = _stable_id_for("task", title or content, id_counts)
                task: dict[str, Any] = {
                    "stable_id": stable_id,
                    "title": title or content,
                    "area": str(metadata.get("area", "triage")),
                    "priority": str(metadata.get("priority", "Triage")),
                    "type": "task",
                }
                if current_feature_id:
                    task["feature_id"] = current_feature_id
                if "estimate_hrs" in metadata:
                    task["estimate_hrs"] = metadata["estimate_hrs"]
                task_deps = _extract_dependency_phrases(heading_text)
                if task_deps["depends_on"]:
                    task["depends_on"] = task_deps["depends_on"]
                if task_deps["blocked_by"]:
                    task["blocked_by"] = task_deps["blocked_by"]
                tasks.append(task)
                continue

        checklist_match = re.match(r"^[-*]\s+\[(?: |x|X)\]\s+(.+)$", stripped)
        if checklist_match:
            raw_item = checklist_match.group(1).strip()
            title, metadata = _extract_tokens(_strip_dependency_phrases(raw_item))
            title = re.sub(r"^task\s*[:\-]\s*", "", title, flags=re.IGNORECASE).strip()
            stable_id = _stable_id_for("task", title, id_counts)
            task: dict[str, Any] = {
                "stable_id": stable_id,
                "title": title,
                "area": str(metadata.get("area", "triage")),
                "priority": str(metadata.get("priority", "Triage")),
                "type": "task",
            }
            if current_feature_id:
                task["feature_id"] = current_feature_id
            if "estimate_hrs" in metadata:
                task["estimate_hrs"] = metadata["estimate_hrs"]
            deps = _extract_dependency_phrases(raw_item)
            if deps["depends_on"]:
                task["depends_on"] = deps["depends_on"]
            if deps["blocked_by"]:
                task["blocked_by"] = deps["blocked_by"]
            tasks.append(task)

    if not epics and not features and not tasks:
        return None

    title = "Structured intake plan"
    if epics:
        title = epics[0]["title"]
    elif features:
        title = features[0]["title"]
    elif tasks:
        title = tasks[0]["title"]

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
                "kind": "markdown_structured",
                "prompt_hash": hashlib.sha256(natural_text.encode("utf-8")).hexdigest()[:16],
            },
        },
        "epics": epics,
        "features": features,
        "tasks": tasks,
    }


def draft_report_ir_from_natural_text(
    *,
    natural_text: str,
    org: str,
    repos: list[str],
    generated_at: str = "",
    mode: str = "basic",
) -> dict[str, Any]:
    if mode == "structured":
        structured_draft = _draft_report_ir_from_structured_markdown(
            natural_text=natural_text,
            org=org,
            repos=repos,
            generated_at=generated_at,
        )
        if structured_draft is not None:
            return structured_draft

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
    preview_nodes: dict[str, list[dict[str, Any]]] = {}
    preview_edges: dict[str, list[dict[str, Any]]] = {}

    known_ids: set[str] = set()
    for item_type in ("epics", "features", "tasks"):
        for item in report_ir.get(item_type) or []:
            if not isinstance(item, dict):
                continue
            stable_id = str(item.get("stable_id", "")).strip()
            if stable_id:
                known_ids.add(stable_id)

    def _add_edge(repo: str, *, edge_type: str, source: str, target: str, provenance: str) -> None:
        if not source or not target:
            return
        if repo not in preview_edges:
            preview_edges[repo] = []
        preview_edges[repo].append(
            {
                "edge_type": edge_type,
                "source": source,
                "target": target,
                "provenance": provenance,
            }
        )

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
            parent_id = ""
            if item_type == "features":
                parent_id = str(item.get("epic_id", "")).strip()
            elif item_type == "tasks":
                parent_id = str(item.get("feature_id", "")).strip()

            blocked_by = [
                str(dep).strip() for dep in (item.get("blocked_by") or []) if str(dep).strip()
            ]
            depends_on = [
                str(dep).strip() for dep in (item.get("depends_on") or []) if str(dep).strip()
            ]

            if repo not in preview_nodes:
                preview_nodes[repo] = []
            preview_nodes[repo].append(
                {
                    "stable_id": stable_id,
                    "title": title,
                    "item_type": item_type[:-1],
                    "parent_id": parent_id,
                    "blocked_by": blocked_by,
                    "depends_on": depends_on,
                }
            )

            if parent_id and parent_id in known_ids:
                _add_edge(
                    repo,
                    edge_type="parent_child",
                    source=parent_id,
                    target=stable_id,
                    provenance="report_ir",
                )
            for blocker_id in blocked_by:
                if blocker_id in known_ids:
                    _add_edge(
                        repo,
                        edge_type="blocked_by",
                        source=stable_id,
                        target=blocker_id,
                        provenance="report_ir",
                    )
            for dependency_id in depends_on:
                if dependency_id in known_ids:
                    _add_edge(
                        repo,
                        edge_type="depends_on",
                        source=stable_id,
                        target=dependency_id,
                        provenance="report_ir",
                    )

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
                    "item_type": item_type[:-1],
                    "stable_id": stable_id,
                    "target_ref": "",
                    "payload": payload,
                    "idempotency_key": idempotency_key,
                }
            )

    entries.sort(key=lambda row: (row["repo"], row["stable_id"], row["operation"]))
    repos = sorted({entry["repo"] for entry in entries})
    dependency_preview = {
        "repos": [
            {
                "repo": repo,
                "nodes": sorted(preview_nodes.get(repo, []), key=lambda node: node["stable_id"]),
                "edges": sorted(
                    preview_edges.get(repo, []),
                    key=lambda edge: (edge["edge_type"], edge["source"], edge["target"]),
                ),
            }
            for repo in repos
        ]
    }
    return {
        "schema_version": "changeset_preview/v1",
        "items": entries,
        "dependency_preview": dependency_preview,
        "summary": {
            "count": len(entries),
            "repos": repos,
            "repo_count": len(repos),
        },
    }
