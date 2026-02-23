# Product specification

This document defines **what pm-bot is supposed to do**.

It is intentionally written as a product spec and a set of invariants (not as an implementation guide).

## Problem statement

pm-bot turns high-level plans into **reliable, org-wide GitHub Issues + Projects** artifacts, while preserving:

- **Human control** (approval gates before anything risky or costly)
- **Determinism** (Projects field sync depends on stable headings)
- **Scalability of use** (local-first today, service later)
- **Auditability** (every write and denial is recorded)

## Goals

### G1 — Plan → previewable diff → approved changes → GitHub reality

Given either:

- a Markdown plan/report containing an embedded machine-readable block (**Mode A**), or
- a plain paragraph that requires LLM extraction (**Mode B**)

pm-bot MUST produce a **previewable diff** (a changeset bundle) describing:

- what issues will be created or updated
- what relationships will be set (parent/child, blocked-by)
- what labels/headings will drive Projects fields
- what agent runs (if any) are proposed

Nothing writes until approved.

### G2 — Projects fields populate deterministically

pm-bot MUST preserve the formatting contract required by the Projects field sync workflow, especially:

- canonical headings
- “first non-empty line after heading” value parsing

### G3 — Tree view is “real, not vibes”

pm-bot MUST represent work structure using durable relationships:

1. GitHub sub-issues (parent/child)
2. GitHub issue dependencies (blocked-by / blocking)
3. Only then, checklist parsing as a fallback

The tree view MUST retain provenance so users know whether an edge came from sub-issues, dependency APIs, or markdown parsing.

### G4 — Agents never spend tokens or write without approval

pm-bot MUST:

- not run LLM-powered agents without a recorded human approval
- not write issues, PRs, or Projects fields without a recorded human approval
- keep privileged GitHub operations separate from agent execution surfaces
- emit machine-readable policy reason codes for every denied write

## Non-goals

- Multi-tenant SaaS / billing (belongs to v3 shape work)
- Full automation (no approval) — pm-bot is “draft-first”, always
- A perfect project management ontology — the goal is deterministic behavior, not philosophical purity

## Core principles and invariants

### P1 — Contract-first data flow

pm-bot’s logic SHOULD be expressed as validated transforms between explicit contracts:

- **ReportIR** (from a plan/report)
- **WorkGraph** (normalized work items + edges)
- **ChangesetBundle** (proposed writes + approvals + execution logs)
- **AgentRunSpec** (proposed token spend + allowed outputs)

These are specified in `docs/contracts/`.

### P2 — Idempotency

Given the same input plan, repeated runs MUST converge:

- they MUST NOT create duplicate issues
- they MUST NOT create duplicate edges or duplicate project-item mutations
- they MUST be safe to “retry” after a partial failure
- bounded retries with dead-letter outcomes must be deterministic and auditable

### P3 — Safety gates are non-bypassable

All mutating operations MUST be mediated by:

- a proposed changeset
- a recorded approval
- execution that records an audit log entry

### P4 — Compatibility with canonical templates/workflows

pm-bot MUST remain compatible with the canonical inputs tracked in the repo:

- `vendor/dotgithub/ISSUE_TEMPLATE/*.yml`
- `vendor/dotgithub/project-field-sync.yml`

If these change, pm-bot must be updated and revalidated.

## Target workflows

### Workflow A — Bring-your-own report (preferred)

1. You generate a Markdown report externally (or by hand).
2. The report contains an embedded machine-readable block (“ReportIR v1”).
3. pm-bot parses the block deterministically (no extra LLM calls).
4. pm-bot maps ReportIR → WorkGraph → proposed ChangesetBundle.
5. You review the diff and approve.
6. pm-bot applies writes to GitHub.
7. Project sync runs and fills project fields.
8. pm-bot records audit and refreshes its local state.

### Workflow B — Paragraph → structured plan (optional)

1. You paste a paragraph or bullets.
2. pm-bot calls an LLM to produce a ReportIR v1 draft.
3. You edit/confirm the ReportIR.
4. Continue as in Workflow A.

### Workflow C — Tree view and dependency overlay

1. pm-bot builds a WorkGraph from GitHub:
   - sub-issues and dependencies where available
   - checklist parsing as a fallback
2. pm-bot renders:
   - an ASCII tree (CLI)
   - optional UI view (tree/graph)
   - export formats (JSON / Mermaid)
3. pm-bot highlights provenance and low-confidence edges.

### Workflow D — Context packs + agent proposals

1. pm-bot builds a context pack for a work item:
   - issue body
   - relevant parent/children
   - dependency context
   - ADR references/snippets (optional)
2. pm-bot proposes an AgentRunSpec (model + budget + allowed outputs).
3. You approve the agent run.
4. The agent produces either:
   - a proposed changeset bundle, or
   - a draft PR
5. You approve the resulting changes before publishing to GitHub.

## Definition of done (release checkpoints)

Use these as “stop/go” gates for shipping.

### DoD-0: Safety + determinism baseline

- Drafting and rendering produces issue bodies that populate Projects fields correctly.
- No write occurs without approval.
- All writes and denials are recorded in an audit trail.

### DoD-1: Plan ingestion

- Mode A supports a deterministic embedded ReportIR block.
- Mapping produces a previewable changeset bundle.
- Re-running ingestion does not duplicate issues.

### DoD-2: GitHub writes + org-scale basics

- pm-bot can create/update/link issues across allowed repos.
- Project items are added and fields updated reliably.
- Rate limits are handled gracefully (bounded concurrency, retries).

### DoD-3: Tree view + estimator + reports

- Tree view uses sub-issues and dependencies where possible.
- Estimator produces explainable P50/P80 (bucketed).
- Weekly meta report is generated.

## Interfaces and their responsibilities

### CLI

Primary responsibilities:

- draft template-compliant issue bodies
- parse issue bodies into canonical WorkItem JSON
- render WorkItem JSON back to deterministic markdown
- show trees / graphs in read-only form
- validate parse/draft payloads with schema + business-rule checks (`--validate`)

Validation guarantees for `--validate`:

- MUST apply JSON Schema validation against `pm_bot/schema/work_item.schema.json`.
- MUST apply deterministic business-rule validators for semantic constraints.
- MUST return machine-readable error payloads with stable `code`, `path`, `message` fields.
- MUST exit non-zero when any validation error exists.

### Server

Primary responsibilities:

- maintain local state (work items, changesets, approvals, audits)
- ingest GitHub webhooks and reconcile state
- generate context packs
- mediate writes through approvals

### Connectors

Primary responsibilities:

- isolate GitHub integration logic
- enforce allowlists/denylists
- handle rate limiting and auth refresh

## Additional specs

The product spec is complemented by more focused specs:

- Graph/tree APIs: `docs/spec/graph-api.md`
- Estimator v1: `docs/spec/estimator.md`
- Meta reporting: `docs/spec/reporting.md`
- Triage inbox: `docs/spec/inbox.md`

## Document map

- Contracts (normative): `docs/contracts/*`
- GitHub execution details (normative for integration): `docs/github/*`
- Runbooks (procedural): `docs/runbooks/*`
- ADRs (design decisions): `docs/adr/*`
- Maintenance rules: `docs/maintenance.md`

