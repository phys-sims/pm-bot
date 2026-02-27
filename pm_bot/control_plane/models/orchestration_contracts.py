from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskSpecV1(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str = "task_spec/v1"
    task_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    inputs: dict[str, Any] = Field(default_factory=dict)


class TaskRunV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "task_run/v1"
    task_run_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    status: str = "pending"
    deps: list[str] = Field(default_factory=list)
    run_id: str = ""
    thread_id: str = ""
    retries: int = 0


class OrchestrationPlanV1(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str = "orchestration_plan/v1"
    plan_id: str = Field(min_length=1)
    repo_id: int = Field(ge=0)
    source: str = Field(min_length=1)
    status: str = "expanded"
    payload: dict[str, Any] = Field(default_factory=dict)
    tasks: list[TaskSpecV1] = Field(default_factory=list)
    edges: list[dict[str, str]] = Field(default_factory=list)


def _task_fingerprint(task: dict[str, Any]) -> str:
    canonical = {
        "title": str(task.get("title", "")).strip(),
        "type": str(task.get("type", "task")).strip() or "task",
        "inputs": task.get("inputs") if isinstance(task.get("inputs"), dict) else {},
        "source_ref": str(task.get("id") or task.get("name") or task.get("title") or "").strip(),
    }
    return json.dumps(canonical, sort_keys=True, separators=(",", ":"))


def _stable_task_id(task: dict[str, Any]) -> str:
    digest = hashlib.sha256(_task_fingerprint(task).encode("utf-8")).hexdigest()
    return f"task_{digest[:16]}"


def expand_plan_payload(
    *, plan_id: str, repo_id: int, source: str, payload: dict[str, Any]
) -> OrchestrationPlanV1:
    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list):
        raw_tasks = payload.get("nodes") if isinstance(payload.get("nodes"), list) else []

    task_rows: list[tuple[TaskSpecV1, str]] = []
    alias_to_task_id: dict[str, str] = {}
    for task in raw_tasks:
        if not isinstance(task, dict):
            continue
        task_id = _stable_task_id(task)
        title = str(task.get("title", "")).strip() or task_id
        inputs = task.get("inputs") if isinstance(task.get("inputs"), dict) else {}
        spec = TaskSpecV1(task_id=task_id, title=title, inputs=inputs)
        task_rows.append((spec, _task_fingerprint(task)))
        for alias in (task.get("id"), task.get("name"), task.get("title"), task_id):
            alias_value = str(alias or "").strip()
            if alias_value:
                alias_to_task_id.setdefault(alias_value, task_id)

    task_rows.sort(key=lambda row: (row[0].task_id, row[1]))
    tasks = [row[0] for row in task_rows]

    edges_set: set[tuple[str, str]] = set()
    for task in raw_tasks:
        if not isinstance(task, dict):
            continue
        to_id = alias_to_task_id.get(
            str(task.get("id") or task.get("name") or task.get("title") or "").strip()
        )
        if not to_id:
            continue
        deps = task.get("deps")
        if not isinstance(deps, list):
            deps = task.get("depends_on") if isinstance(task.get("depends_on"), list) else []
        for dep in deps:
            from_id = alias_to_task_id.get(str(dep).strip())
            if from_id and from_id != to_id:
                edges_set.add((from_id, to_id))

    for edge in payload.get("edges", []) if isinstance(payload.get("edges"), list) else []:
        if not isinstance(edge, dict):
            continue
        from_alias = str(
            edge.get("from") or edge.get("from_id") or edge.get("from_task") or ""
        ).strip()
        to_alias = str(edge.get("to") or edge.get("to_id") or edge.get("to_task") or "").strip()
        from_id = alias_to_task_id.get(from_alias)
        to_id = alias_to_task_id.get(to_alias)
        if from_id and to_id and from_id != to_id:
            edges_set.add((from_id, to_id))

    edges = [
        {"from_task": from_task, "to_task": to_task}
        for from_task, to_task in sorted(edges_set, key=lambda item: (item[0], item[1]))
    ]
    return OrchestrationPlanV1(
        plan_id=plan_id,
        repo_id=repo_id,
        source=source,
        payload=payload,
        tasks=tasks,
        edges=edges,
    )
