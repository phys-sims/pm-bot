# Graph and tree API specification

pm-bot exposes graph/tree views via server APIs (and optionally a UI).

The purpose is to make hierarchy and dependencies decision-grade.

## Core capabilities

- Tree view: epic → feature → task
- Dependency overlay: blocked-by edges
- Rollups:
  - closed children / total children
  - estimate rollups (optional)
- Provenance indicators:
  - sub-issue vs dependency API vs checklist-derived

## Recommended endpoints (shape)

Actual endpoints may differ; this spec describes recommended semantics.

### `GET /graph/tree`

Query params:

- `root`: issue URL, issue number, or stable_id
- `max_depth`: optional
- `include_deps`: optional bool
- `provenance`: optional filter (`sub_issue`, `checklist`, ...)

Response (recommended):

- `root` node
- `nodes` list with:
  - stable_id
  - title
  - type
  - status
  - key fields (area/priority/size)
- `edges` list with:
  - from/to stable_ids
  - edge_type
  - provenance
- `warnings` list:
  - cycles detected
  - conflicts between sources
  - unresolved references

### `GET /graph/deps`

Query params:

- `area` (optional)
- `status` (optional)
- `repo` (optional)

Response:

- filtered edges and nodes
- summary counts
- warnings list that can include `partial_ingestion` diagnostics when connector ingestion had recoverable failures

### `POST /graph/ingest`

Request body:

- `repo` (required): `org/repo`

Response:

- ingestion diagnostics snapshot:
  - `calls`
  - `failures`
  - `partial`
  - `edge_count`
  - structured diagnostics payload for replay/debugging

## Cycle behavior (normative)

If a cycle exists in parent/child edges:

- tree endpoint MUST return a warning
- tree endpoint SHOULD return partial data plus cycle diagnostics, or fail closed (choose one and document)

## Provenance behavior (normative)

Edges MUST include provenance.

When multiple edges conflict, the endpoint MUST:

- prefer sub-issue edges for hierarchy
- preserve conflicting info in warnings/diagnostics

Graph ingestion SHOULD collect sub-issue and dependency edges with provenance and timestamps, while preserving partial-ingestion diagnostics instead of failing the full sync when possible.

## Performance constraints (recommended)

- endpoints SHOULD support pagination or lazy loading
- avoid fetching entire org graphs by default

## References

- `docs/github/tree-and-dependencies.md` (source priority + provenance)
- `docs/contracts/workgraph.md` (edge types and constraints)
