# Board snapshot + replanner flow
> **Audience:** Contributors maintaining board drift detection and automated adjustment proposal flow.
> **Depth:** L2 (behavioral specification).
> **Source of truth:** Normative runtime behavior for snapshot capture, drift scoring, replanner triggering, and audit trail outputs.

## Contract anchors

- LLM capability classes and guardrails: [`docs/contracts/llm_capabilities.md`](../contracts/llm_capabilities.md)
- Changeset proposal/approval contract: [`docs/contracts/changesets.md`](../contracts/changesets.md)
- Work graph structure/provenance contract: [`docs/contracts/workgraph.md`](../contracts/workgraph.md)

## Flow overview

`board_snapshot_replanner_flow` executes this deterministic sequence:

1. Load latest persisted snapshot for repo.
2. Capture and persist a current snapshot (`board_snapshot/v1`).
3. Compute diff (`board_snapshot_diff/v1`) and `drift_score`.
4. Evaluate significance threshold.
5. If significant drift and a prior snapshot exists, run `issue_replanner` capability and convert bundle entries into approval-gated changeset proposals.
6. Persist diff row and append audit event `board_snapshot_diff_recorded`.
7. Return `board_replanner_flow/v1` result containing snapshot, diff row, and proposal summary.

## Snapshot capture semantics (`board_snapshot/v1`)

Per issue, normalized fields are:

- `issue_ref` (required key)
- `title`
- `status`:
  - `closed` when issue state is closed
  - else explicit `status` / `project_status`
  - else first `labels[]` token with prefix `status:`
  - else fallback `open`
- `blockers`: sorted unique list from `blocked_by`/`blockers` (string or list input)
- `age_days`: rounded age from created/opened timestamp to capture time (invalid/missing timestamps resolve to `0.0`)

Snapshot summary includes deterministic counts:

- `issue_count`
- `blocked_count`
- `status_counts` keyed by normalized status

## Diff + drift semantics (`board_snapshot_diff/v1`)

Diff output includes:

- `added_issue_refs[]` and `removed_issue_refs[]` (sorted)
- `status_changes[]`
- `blocker_changes[]`
- `age_changes[]` only when absolute age delta is `>= 3.0` days

Drift score formula:

`added + removed + status_changes + blocker_changes + (0.5 * age_changes)`

Rounded to two decimals.

## Trigger thresholds (normative)

Significant drift is true when either condition holds:

- `drift_score >= 3.0`, OR
- at least one blocker change and `drift_score >= 2.0`

Initial snapshot runs (no previous snapshot) MUST NOT invoke replanner proposals.

## Replanner lifecycle (`issue_replanner`)

When triggered:

- Capability id: `issue_replanner`
- Capability class: `mutation_proposal`
- Policy MUST enforce:
  - `proposal_output_changeset_bundle=true`
  - `require_human_approval=true`
  - no direct GitHub writes

Input payload includes `repo`, `previous_snapshot_id`, `current_snapshot_id`, and computed diff object.

Output bundle `changesets[]` entries are translated into `propose_changeset(...)` calls and remain pending approval under existing changeset contract semantics.

## Audit + persistence requirements

The flow MUST persist:

- `board_snapshots` row for current snapshot.
- `board_snapshot_diffs` row with `drift_score`, significance, replanner trigger flag, proposal count, and run id.
- Audit event `board_snapshot_diff_recorded` with snapshot ids, diff id, drift metadata, and trigger source.

When replanner runs, it MUST append `issue_replanner_triggered` including run id, actor, repo, capability id, and snapshot ids.

## Result envelope (`board_replanner_flow/v1`)

Returned object includes:

- `schema_version=board_replanner_flow/v1`
- `repo`
- `snapshot`
- `diff` (persisted diff row)
- `significant_drift`
- `proposals[]`
- `summary` with `proposal_count` and `triggered_replanner`
