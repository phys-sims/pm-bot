# PM agent native spec (navigator spec)

Role: **Navigator spec**. This document provides a single integrated overview and links to authoritative sources. It MUST NOT redefine normative contract fields or duplicate subsystem rules that are already defined in contracts/specs.

## Source of truth pointers

- Canonical template/workflow inputs:
  - `vendor/dotgithub/ISSUE_TEMPLATE/*.yml`
  - `vendor/dotgithub/issue-templates-guide.md`
  - `vendor/dotgithub/project-field-sync.yml`
- Schema and contract authority:
  - `pm_bot/schema/work_item.schema.json`
  - `docs/contracts/workgraph.md`
  - `docs/contracts/context_pack.md`
  - `docs/contracts/changesets.md`
  - `docs/contracts/agent_run_spec.md`
- Parse/render behavior authority:
  - `docs/github/projects-field-sync.md`
  - `docs/spec/product.md`
- GitHub sync behavior authority:
  - `docs/github/projects-field-sync.md`
  - `docs/github/tree-and-dependencies.md`
  - `docs/github/auth-and-tokens.md`
- Approvals and guarded writes authority:
  - `docs/contracts/changesets.md`
  - `docs/contracts/agent_run_spec.md`
  - `docs/adr/ADR-0001-approval-gated-writes.md`
- Estimator and reporting authority:
  - `docs/spec/estimator.md`
  - `docs/spec/reporting.md`

---

## Purpose

Use this document as a fast orientation map for humans and agents who need to understand how pm-bot components fit together without introducing competing definitions.

## System map (non-normative summary)

pm-bot operates as a deterministic, contract-first orchestration stack:

1. Ingest canonical GitHub template/workflow inputs from `vendor/dotgithub/...`.
2. Parse/render issue content with heading compatibility preserved for Project sync.
3. Normalize state into contract-driven structures (WorkGraph, ContextPack, Changesets, AgentRunSpec).
4. Run guarded write flows with approvals + auditability.
5. Provide estimator snapshots and reporting from captured outcomes.

For exact requirements, follow the source documents in the next sections.

## Where to read by task

### Template and field compatibility
- `docs/github/projects-field-sync.md`
- `vendor/dotgithub/project-field-sync.yml`
- `vendor/dotgithub/ISSUE_TEMPLATE/*.yml`

### Parse/render and CLI behavior
- `docs/spec/product.md`
- `docs/github/projects-field-sync.md`

### Graph/tree semantics
- `docs/contracts/workgraph.md`
- `docs/spec/graph-api.md`
- `docs/github/tree-and-dependencies.md`

### Context pack structure and guarantees
- `docs/contracts/context_pack.md`

### Approvals, write safety, and auditability
- `docs/contracts/changesets.md`
- `docs/contracts/agent_run_spec.md`
- ADR trail via `docs/adr/INDEX.md` (tags: safety, approvals, github)

### Estimation and meta-reporting
- `docs/spec/estimator.md`
- `docs/spec/reporting.md`

## ADR navigation

Use `docs/adr/INDEX.md` first, then open only ADRs whose tags match your change domain (for example: `contracts`, `github`, `auth`, `safety`, `tree`, `reporting`).

## Change-control reminder

When contract/spec behavior changes, update this navigator only to fix links or scope summaries. Do not add duplicate normative rules here; place normative changes in the appropriate contract/spec source.
