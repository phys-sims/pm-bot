# Orchestration Plan v1
> **Audience:** Contributors implementing plan expansion, scheduling, and execution persistence.
> **Depth:** L3 (normative contract).
> **Source of truth:** Contract for plan expansion (`orchestration_plan/v1`), task specs (`task_spec/v1`), and task runs (`task_run/v1`).

## Purpose

This contract makes `plan -> tasks -> dependencies` explicit and deterministic.

## Contract objects

### `orchestration_plan/v1`

Required fields:

- `schema_version`: `orchestration_plan/v1`
- `plan_id`: stable external plan identifier.
- `repo_id`: local repository registry ID (`repo_registry.id`).
- `source`: ingestion/expansion source (`api`, `report_ir`, etc.).
- `status`: orchestration lifecycle state (`expanded` in v1).
- `payload`: canonical expanded payload including tasks and edges.

### `task_spec/v1`

Required fields:

- `schema_version`: `task_spec/v1`
- `task_id`: deterministic task identifier for a task spec.
- `title`: canonical task title.
- `inputs`: execution inputs payload.

### `task_run/v1`

Required fields:

- `schema_version`: `task_run/v1`
- `task_run_id`: task-run identifier (`<plan_id>:<task_id>` in v1).
- `plan_id`: owning plan.
- `task_id`: resolved deterministic task ID.
- `status`: execution status (`pending` default).
- `deps`: task IDs this task depends on.
- `run_id`: optional adapter run linkage.
- `thread_id`: optional thread linkage.
- `retries`: retry counter.

## Determinism guarantees

For identical plan payloads:

- expanded `task_id` values MUST be identical.
- edge list (`from_task`, `to_task`) MUST be identical and sorted.
- dependency lists in `task_run` records MUST be sorted.

## Storage mapping

- `orchestration_plan` table stores expanded payload and plan metadata.
- `task_runs` stores task-level execution state.
- `task_edges` stores normalized DAG edges.
