# Tree and dependencies
> **Audience:** Contributors implementing hierarchy and dependency sync.
> **Depth:** L2 (integration behavior detail).
> **Source of truth:** Normative derivation and precedence behavior for tree/dependency integration.


pm-bot supports a “tree view” of work (epic → feature → task) and an overlay of dependencies (“blocked by”).

This document defines:

- where tree/dependency edges come from
- how provenance is tracked
- how conflicts and cycles are handled

## Relationship sources (priority order)

pm-bot SHOULD derive structure in this order:

1. **GitHub sub-issues** (canonical parent/child)
2. **GitHub issue dependencies** (blocked-by / blocking)
3. **Markdown checklist parsing** (fallback only)

Rationale:

- sub-issues and dependency APIs are machine-readable and less error-prone than parsing markdown conventions
- checklist parsing exists for backward compatibility and “quick drafting” workflows

## Edge types

### Parent/child (`parent_child`)

Represents hierarchy:

- Epic contains Features
- Feature contains Tasks (or typed tasks like Bug/Test/Spike)

Canonical backend source: GitHub sub-issues.

### Dependencies (`depends_on`, `blocked_by`)

Represents scheduling constraints:

- “A depends on B”
- “A is blocked by B”

Canonical backend source: GitHub dependencies endpoints.

### Related

Represents non-scheduling links (optional).

## Provenance

Every edge MUST include provenance:

- `sub_issue`
- `dependency_api`
- `checklist`
- `report_ir`
- `manual`

Provenance is crucial because:

- it tells you whether an edge is trustworthy
- it tells you whether pm-bot should try to “repair” drift automatically

## Checklist parsing rules (fallback)

When using checklist parsing, pm-bot SHOULD support the common patterns:

- `- [ ] #123`
- `- [x] #123`
- `- [ ] https://github.com/org/repo/issues/123`
- `- [ ] org/repo#123`

Rules:

- only checklist items that resolve to valid issue references count as edges
- unchecked vs checked MAY be used to infer “done” status, but should not be treated as authoritative
- checklist-derived edges MUST be labeled `provenance = "checklist"`

## Conflict resolution

### When multiple sources disagree

Example: sub-issues say Feature A is under Epic X, but checklist says Epic Y.

Policy (recommended):

1. Prefer `sub_issue` over `checklist`.
2. Preserve both edges in diagnostics, but only render the preferred edge in “tree view”.
3. Surface a warning: “Checklist-derived hierarchy conflicts with sub-issue hierarchy”.

### When ReportIR proposes edges that conflict with GitHub

Policy (recommended):

- treat ReportIR edges as proposals, not facts
- convert them into changesets for review
- after applying, the new GitHub relationships become canonical

## Cycle handling

Cycles can occur accidentally (especially with manual sub-issue edits).

pm-bot MUST:

- detect cycles when rendering a tree view
- refuse to render a misleading tree
- surface the cycle path so it can be fixed

Recommended behavior:

- show a minimal cycle example:
  - `epic:A -> feat:B -> epic:A`
- suggest a fix:
  - remove one parent/child edge

## Cross-repo considerations

Hierarchy across repos can be tricky depending on GitHub features and org settings.

Recommended approach:

- allow cross-repo edges in WorkGraph
- store them as edges with bindings to issue URLs
- render tree views with clear repo annotations

Checklist parsing is often the easiest cross-repo fallback when sub-issues aren’t available across repos.

## Testing tree behavior

Use the runbook:

- `docs/runbooks/first-human-test.md`

Specifically, create a small structure:

- one epic
- two features
- two tasks under one feature
- add one dependency edge between tasks

Then verify:

- tree view renders
- dependency overlay renders
- provenance labels make sense

