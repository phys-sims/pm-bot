# pm-bot documentation IA
> **Audience:** Contributors and maintainers navigating documentation.
> **Depth:** L0 (documentation IA).
> **Source of truth:** Canonical source for documentation architecture and precedence.


This file is the canonical documentation information architecture for pm-bot.

## Documentation depth model

- **L0 (orientation):** `README.md`, `docs/README.md`.
  - Goal: quick navigation and entrypoint constraints.
  - Target: `<~200` lines per page.
- **L1 (procedural usage):** `docs/quickstart.md`, `docs/runbooks/*.md`.
  - Goal: operational steps and verification procedures.
  - Rule: link to L2/L3 for deep contract/behavior detail instead of duplicating it.
- **L2 (behavior and integration detail):** `docs/spec/*.md`, `docs/github/*.md`.
  - Goal: normative behavior and integration semantics.
  - Rule: use RFC 2119 language (`MUST`, `SHOULD`, `MAY`) consistently.
- **L3 (normative contract truth):** `docs/contracts/*.md`, `pm_bot/schema/*.json`.
  - Goal: canonical data-shape and validation truth.
  - Rule: L3 supersedes L2/L1 when fields, invariants, or schemas conflict.

## Documentation precedence (authoritative)

When documents conflict, resolve in this order:

1. **Canonical inputs** (`vendor/dotgithub/...`)
   - `vendor/dotgithub/ISSUE_TEMPLATE/*.yml`
   - `vendor/dotgithub/issue-templates-guide.md`
   - `vendor/dotgithub/project-field-sync.yml`
2. **Machine-readable schemas and contract docs**
   - `pm_bot/schema/work_item.schema.json`
   - `docs/contracts/*.md`
3. **Behavior specs** (`docs/spec/*.md`)
4. **Architecture decisions** (`docs/adr/INDEX.md` + relevant ADRs)
5. **Operational status** (`STATUS.md`)
6. **Planning artifacts** (`docs/roadmaps/*.md`, `docs/archive/roadmaps/*.md`, `docs/implementation/roadmap-prompts/*.md`)

Roadmaps are planning aids only and MUST NOT override higher-precedence sources.

**Roadmaps policy:** roadmap documents follow a lifecycle of **active → archived → removed**. Active plans stay in `docs/roadmaps/`; once superseded, they move to `docs/archive/roadmaps/` for historical reference; stale artifacts with no ongoing planning value are removed.

## Section ownership by folder

- `docs/spec/` — product and subsystem behavior definitions (what the system should do).
- `docs/contracts/` — normative data/interface contracts and invariants.
- `docs/github/` — GitHub integration contracts, template/project sync behavior, auth guidance.
- `docs/adr/` — long-lived architecture/policy decisions and rationale.
- `docs/runbooks/` — repeatable operational/human test procedures.
- `docs/examples/` — concrete contract payload examples tied to schemas/specs.
- `docs/roadmaps/` — active sequencing/planning only (non-normative).
- `docs/archive/roadmaps/` — archived planning history (non-authoritative).
- `docs/implementation/roadmap-prompts/` — internal roadmap prompt/meta-generation assets (tooling support only).
- `docs/qa-matrix.md` — test and CI command mapping.
- `docs/maintenance.md` — documentation governance and hygiene workflows.

## For agents

Agent-specific intake rules, required first reads, and change-type triggers are
centralized in [`docs/agents/README.md`](agents/README.md) instead of being
duplicated across multiple docs.

## Navigation

- Product behavior anchor: [`docs/spec/product.md`](spec/product.md)
- Contracts index:
  - [`docs/contracts/report_ir_v1.md`](contracts/report_ir_v1.md)
  - [`docs/contracts/workgraph.md`](contracts/workgraph.md)
  - [`docs/contracts/changesets.md`](contracts/changesets.md)
  - [`docs/contracts/agent_run_spec.md`](contracts/agent_run_spec.md)
- GitHub integration:
  - [`docs/github/projects-field-sync.md`](github/projects-field-sync.md)
  - [`docs/github/auth-and-tokens.md`](github/auth-and-tokens.md)
  - [`docs/github/tree-and-dependencies.md`](github/tree-and-dependencies.md)
- Active planning index: [`docs/roadmaps/README.md`](roadmaps/README.md)
- Archived planning index: [`docs/archive/roadmaps/README.md`](archive/roadmaps/README.md)
- Operational health: [`STATUS.md`](../STATUS.md)

## Entry-point boundary rules

- `README.md` MUST stay brief: orientation + install/run + links only.
- `docs/README.md` is the only authoritative location for documentation IA and precedence.
- `STATUS.md` MUST contain only: runtime `Last updated`, CI health checklist, current compatibility notes, and active change scope bullets.
