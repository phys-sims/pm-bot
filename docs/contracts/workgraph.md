# WorkGraph

WorkGraph is pm-bot’s normalized representation of work across repositories:

- **WorkItems** (nodes): epics, features, tasks, bugs, spikes, etc.
- **WorkEdges** (edges): parent/child relationships, dependencies, and other links.

WorkGraph is intentionally independent of GitHub formatting:

- it is not “issue body markdown”
- it is not “GitHub API payload”
- it is the normalized graph that pm-bot can render into different backends (GitHub now, others later)

## Design goals

WorkGraph MUST:

- represent work items in a consistent, backend-independent way
- carry enough metadata to render into canonical GitHub templates
- encode relationships with explicit types and provenance
- support idempotent reconciliation (stable IDs)

WorkGraph SHOULD:

- keep GitHub-specific IDs (issue number, node id) as optional “bindings”
- remain readable in JSON for debugging and review

## Core types

### WorkItem

A WorkItem represents a single unit of work.

#### Required fields

- `stable_id` (string): global stable identifier (used for idempotency)
- `type` (string): one of:
  - `epic`
  - `feature`
  - `task`
  - `bug`
  - `benchmark`
  - `spike`
  - `test`
  - `chore`
- `title` (string)

#### Recommended fields (used to populate GitHub templates/Projects)

- `area` (string)
- `priority` (string)
- `size` (string)
- `estimate_hrs` (number)
- `risk` (string)
- `blocked_by` (array[string]): stable IDs or URLs (optional convenience; edges are still canonical)
- `actual_hrs` (number)
- `status` (string): e.g. backlog / in-progress / done

#### Description fields

- `body_markdown` (string): canonical rendered body (optional at graph stage)
- `summary` (string): short one-liner
- `acceptance_criteria` (array[string])

#### GitHub binding fields (optional)

These MUST be treated as “bindings”, not identity:

- `github` (object, optional):
  - `org` (string)
  - `repo` (string)
  - `issue_number` (number)
  - `issue_node_id` (string)
  - `url` (string)
  - `project_item_id` (string)

### WorkEdge

A WorkEdge represents a typed relationship between two WorkItems.

#### Required fields

- `from_id` (string): stable_id of source node
- `to_id` (string): stable_id of destination node
- `edge_type` (string): one of:
  - `parent_child`
  - `depends_on`
  - `blocked_by`
  - `related`
  - `duplicates` (optional)
- `provenance` (string): where this edge came from (see below)

#### Provenance (recommended enum)

- `sub_issue` — derived from GitHub sub-issues
- `dependency_api` — derived from GitHub dependencies endpoints
- `checklist` — derived from parsing markdown checklists
- `report_ir` — derived from ReportIR ingestion
- `manual` — created by a human in pm-bot UI/CLI

## Graph constraints

### Identity

- A WorkItem’s identity is its `stable_id`.
- GitHub identifiers (issue numbers, URLs) are bindings that may change or be absent.

### Parent/child constraints

- `parent_child` edges SHOULD be a tree/forest:
  - each node has at most one parent in a given hierarchy (unless explicitly supported)
  - cycles MUST be rejected (cycle detection required)

If the source data contains a cycle (e.g., mistaken sub-issue wiring), pm-bot MUST:

- refuse to render a “tree” view
- surface a diagnostic showing the cycle path
- preserve the raw edges for correction

### Dependency constraints

- `depends_on` and `blocked_by` edges MAY form general graphs.
- Cycles are possible but should be surfaced (they typically indicate planning errors).

## Source priority for building WorkGraph from GitHub

When deriving WorkGraph from GitHub, pm-bot SHOULD prioritize sources in this order:

1. `sub_issue`
2. `dependency_api`
3. `checklist`

This is documented in detail in `docs/github/tree-and-dependencies.md`.

## Mapping: WorkGraph → GitHub

WorkGraph is mapped into GitHub issues using the canonical templates.

### Key constraint: deterministic headings

The Projects sync workflow reads headings from issue bodies and uses the first non-empty line under each heading as the field value.

Therefore, the GitHub renderer MUST:

- output canonical headings exactly
- ensure the intended value appears on the first non-empty line after the heading
- avoid “help text” or bullets before the value line

See `docs/github/projects-field-sync.md`.

### Labels and headings

pm-bot SHOULD set both:

- labels (for quick filtering and redundancy)
- headings (for Projects sync fields)

This enables Projects field sync even if labels drift, and keeps issues usable without the Project.

## Example WorkGraph JSON

```json
{
  "schema_version": "workgraph/v1",
  "nodes": [
    {
      "stable_id": "epic:docs",
      "type": "epic",
      "title": "Documentation hardening",
      "area": "pm-bot",
      "priority": "P1"
    },
    {
      "stable_id": "feat:contracts",
      "type": "feature",
      "title": "Contract-first docs",
      "area": "pm-bot",
      "priority": "P1"
    }
  ],
  "edges": [
    {
      "from_id": "epic:docs",
      "to_id": "feat:contracts",
      "edge_type": "parent_child",
      "provenance": "report_ir"
    }
  ]
}
```

## WorkItem validation behavior

When WorkItem-like JSON is produced by parser/draft flows, validation is contractually split into two layers:

1. Schema checks (required fields, enums, numeric constraints) using `pm_bot/schema/work_item.schema.json`.
2. Business-rule checks for semantic constraints, including:
   - required template heading semantics (for example empty required headings),
   - reference validity (for example child issue refs must be issue numbers or issue URLs),
   - type-specific requirements (for example task `Parent Feature URL` content).

Consumers should treat validator `code` values as stable automation contracts.

## Versioning

- `schema_version` MUST be versioned.
- Breaking changes require a new WorkGraph version.

