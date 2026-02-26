# Agent documentation map
> **Audience:** Automated and human agents executing repository changes.
> **Depth:** L1 (procedural intake).
> **Source of truth:** Canonical intake map for required reads by change type.

Use this page as the canonical map for what to read before changing code or docs.

## Required first reads

1. `STATUS.md` (current repository health, constraints, and active deltas).
2. `AGENTS.md` (policy and workflow rules for this repository).
3. `docs/adr/INDEX.md` before changing architecture, schema contracts, workflow behavior, or policy/safety logic.

Then read only the domain docs needed for the touched change type.

## Trigger matrix

> Sync note: this matrix must stay identical to `AGENTS.md` and is validated by `tests/test_agent_docs_sync.py`.

| Change type | Minimum required docs |
| --- | --- |
| Architecture, data model, safety policy, workflow semantics | `STATUS.md`; `docs/adr/INDEX.md`; ADRs tagged for touched domains |
| Schema/contract fields, parser-renderer contracts, compatibility labels | `STATUS.md`; ADR index + relevant tagged ADRs; `docs/contracts/*.md`; canonical inputs listed in `AGENTS.md` |
| Runtime behavior or decision logic | `STATUS.md`; ADR index + relevant tagged ADRs; `docs/spec/*.md` |
| GitHub/project integration or sync workflow behavior | `STATUS.md`; ADR index + relevant tagged ADRs; `docs/github/*.md`; `vendor/dotgithub/project-field-sync.yml` |
| Roadmap/task sequencing only | `STATUS.md`; roadmap docs (planning aid only) |

## Domain documentation links

- Contracts: `docs/contracts/*.md`
- Behavior specs: `docs/spec/*.md`
- GitHub integration: `docs/github/*.md`
- ADR index: `docs/adr/INDEX.md`
- Canonical inputs:
  - `vendor/dotgithub/ISSUE_TEMPLATE/*.yml`
  - `vendor/dotgithub/issue-templates-guide.md`
  - `vendor/dotgithub/project-field-sync.yml`
  - `pm_bot/schema/work_item.schema.json`

## Scope and precedence reminder

- Roadmaps are sequencing aids and MUST NOT override canonical inputs, contracts, or specs.
- Prefer deterministic, schema-driven updates over prose-only guidance when contracts exist.
