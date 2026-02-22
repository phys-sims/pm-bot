# Hierarchy derivation uses sub-issues first, then dependencies, then checklists

- **ADR ID:** ADR-0004
- **Status:** Proposed
- **Date:** 2026-02-22
- **Deciders:** @you
- **Area:** github
- **Related:** `pm_bot/server/graph.py`, checklist parsing in `pm_bot/github/parse_issue_body.py`
- **Tags:** tree, github, provenance, safety
- **Scope:** repo
- **Visibility:** public

## Context

pm-bot needs a trustworthy tree view of work.

Historically, many orgs used markdown checklists in epic/feature bodies to represent hierarchy.

GitHub now supports more durable primitives:

- sub-issues (parent/child)
- issue dependencies (blocked-by)

We need a clear rule for which source of hierarchy to trust.

## Options considered

### Option A — Checklist parsing as the canonical hierarchy source

- **Description:** treat checklists in templates as the tree-of-record.
- **Pros:**
  - works everywhere (including cross-repo references)
  - aligns with how many templates are written today
- **Cons:**
  - parsing is brittle (writing style differences)
  - hard to enforce correctness
  - low confidence compared to native relationships
- **Risks / Unknowns:**
  - easy for humans to drift from convention
- **Testing impact:**
  - requires extensive parsing fixtures

### Option B — Sub-issues canonical, with checklist fallback

- **Description:** prefer GitHub sub-issues for parent/child; use dependencies for blocked-by; parse checklists only as fallback or legacy import.
- **Pros:**
  - uses native machine-readable structures
  - supports richer operations (reorder, list, remove) without parsing markdown
  - makes tree view more reliable
- **Cons:**
  - may not support every cross-repo hierarchy scenario
  - requires API access and potentially additional permissions
- **Risks / Unknowns:**
  - depends on org GitHub features and adoption
- **Testing impact:**
  - fewer parsing edge cases; more integration tests

### Option C — Maintain two hierarchies in parallel

- **Description:** always parse checklists and also read sub-issues, then attempt to keep them consistent.
- **Pros:**
  - maximal backward compatibility
- **Cons:**
  - doubles complexity and drift risk
  - unclear which source wins in conflicts
- **Risks / Unknowns:**
  - high maintenance burden

## Decision

- **Chosen option:** Option B — sub-issues first, dependencies second, checklists fallback.
- **Rationale:** tree view must be decision-grade. Native GitHub relationships are more reliable than markdown parsing.
- **Trade-offs:** we accept that some cross-repo cases may still need checklists as a fallback.
- **Scope of adoption:** all tree rendering and graph APIs must prioritize these sources and attach provenance.

## Consequences

### Positive

- Tree view becomes more trustworthy.
- Provenance enables debugging and gradual migration away from checklists.

### Negative / mitigations

- Cross-repo limitations.
  - Mitigation: allow checklist-derived edges for cross-repo links; mark provenance accordingly.

### Migration plan

1. In graph builder:
   - ingest sub-issue edges and dependency edges when available
2. Parse checklists only if:
   - no sub-issue structure exists, or
   - user explicitly requests “legacy checklist import”
3. Always attach provenance and surface conflicts.

### Test strategy

- Unit tests:
  - checklist parsing correctness for known patterns
  - provenance labeling
- Integration tests (sandbox):
  - sub-issue hierarchy fetched correctly
  - dependency edges fetched correctly
- Human runbook:
  - create a small graph and verify UI/CLI output

### Docs updates required

- `docs/github/tree-and-dependencies.md`

## Open questions

- Should pm-bot provide a migration tool: checklist → sub-issues?
- Should checklist-derived edges ever be auto-applied, or always proposed as changesets?

## References

- `docs/github/tree-and-dependencies.md`

## Changelog

- 2026-02-22 — Proposed by @you

