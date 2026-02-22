# Documentation and contract maintenance

This file defines how pm-bot documentation stays correct over time.

## Golden rule

If you change behavior, you must update:

- the relevant docs
- the relevant schemas/examples
- `STATUS.md`
- tests

## What each document type is for

### `STATUS.md`

- **Purpose:** current truth of “what exists” and “what is compatible”.
- **Update on:** any behavior, schema, workflow, or canonical input change.
- **Audience:** agents and maintainers who need a quick, authoritative overview.

### `docs/spec/*`

- **Purpose:** product intent and invariants (“what pm-bot should do”).
- **Update on:** user-visible workflow changes, major policy changes.

### `docs/contracts/*`

- **Purpose:** normative data contracts (ReportIR/WorkGraph/Changesets/AgentRunSpec).
- **Update on:** any contract change, schema change, or validation rule change.
- **Also update:** `docs/examples/*` + schema validation tests.

### `docs/github/*`

- **Purpose:** GitHub-specific contracts and pitfalls.
- **Update on:** template changes, Projects workflow changes, auth strategy changes.

### `docs/runbooks/*`

- **Purpose:** repeatable human procedures and QA gates.
- **Update on:** new failure modes or new setup/verification steps.

### `docs/adr/*`

- **Purpose:** design decisions (“why we did it this way”).
- **Update on:** architecture changes, trade-off choices, long-lived decisions.

### Roadmaps (`agent-roadmap-*.md`, `future-roadmap.md`, `human-roadmap.md`)

- **Purpose:** planning and sequencing.
- **Update on:** priorities/timelines; not used as a contract.

## Required updates by change type

### If you change issue templates

Examples:

- rename a heading
- change required fields
- add a new issue type

You MUST update:

- `vendor/dotgithub/ISSUE_TEMPLATE/*.yml` snapshot (if vendorized)
- `pm_bot/schema/work_item.schema.json` and `template_map.json` (if derived)
- parser/renderer tests
- `docs/github/projects-field-sync.md` (if headings/field parsing impacted)
- `STATUS.md`

### If you change Projects field sync behavior

You MUST update:

- `vendor/dotgithub/project-field-sync.yml`
- `docs/github/projects-field-sync.md`
- end-to-end human test runbook results (re-run it)
- `STATUS.md`

### If you change the approval model or changesets

You MUST update:

- `docs/contracts/changesets.md`
- `docs/runbooks/first-human-test.md`
- any UI/CLI approval docs
- `STATUS.md`

### If you introduce or change ReportIR / ingestion

You MUST update:

- `docs/contracts/report_ir_v1.md`
- `docs/contracts/workgraph.md` (mapping rules)
- `docs/examples/report_ir_v1.example.json`
- schema validation tests

### If you change GitHub auth strategy

You MUST update:

- `docs/github/auth-and-tokens.md`
- any setup docs that mention tokens
- ADR (if the change is architectural)

## Doc review checklist for PRs

Before merging, ask:

- Did we update `STATUS.md` scope bullets?
- Did we update the relevant contract doc(s)?
- If contracts/specs changed, did we verify no contradictory statements remain between `docs/README.md`, `docs/spec/*.md`, and `docs/contracts/*.md`?
- Did we update example JSON and validation tests?
- Did we preserve Projects sync invariants?
- If this is a design change, did we add/supersede an ADR?

## Keeping docs agent-friendly

Agents are most effective when:

- key decisions are in ADRs (indexed + tagged)
- contracts are explicit and have examples
- the “canonical sources” are clear

Avoid “narrative-only” docs without examples or invariants.

