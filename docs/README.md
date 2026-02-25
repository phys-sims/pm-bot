# pm-bot documentation

This `docs/` folder is the **human-readable spec + contracts + runbooks** for pm-bot.

It is designed for two audiences:

- **Humans** who want to use pm-bot to go from a plan → GitHub Issues/Projects safely.
- **Agents** who need a reliable “design map” before making changes.

## How to navigate

### If you are trying to use pm-bot (daily driver)

1. Read **Quickstart**: [`docs/quickstart.md`](quickstart.md)
2. Run the **First Human Test** checklist once (sandbox repo): [`docs/runbooks/first-human-test.md`](runbooks/first-human-test.md)
3. When something looks wrong, consult:
   - GitHub Projects sync contract: [`docs/github/projects-field-sync.md`](github/projects-field-sync.md)
   - Tree + dependency rules: [`docs/github/tree-and-dependencies.md`](github/tree-and-dependencies.md)

### If you are implementing or changing pm-bot

1. Read the **Product Spec**: [`docs/spec/product.md`](spec/product.md)
2. Treat the following as **contracts** (changing them requires care):
   - ReportIR v1: [`docs/contracts/report_ir_v1.md`](contracts/report_ir_v1.md)
   - WorkGraph: [`docs/contracts/workgraph.md`](contracts/workgraph.md)
   - Changesets + approvals: [`docs/contracts/changesets.md`](contracts/changesets.md)
   - AgentRunSpec: [`docs/contracts/agent_run_spec.md`](contracts/agent_run_spec.md)
3. If your change is a “design decision”, write an ADR:
   - ADR guide: [`docs/adr/README.md`](adr/README.md)
   - ADR index (generated): [`docs/adr/INDEX.md`](adr/INDEX.md)

### If you are a code-writing agent

Minimum reading order:

1. `STATUS.md` (source-of-truth for current repo state and canonical inputs)
2. `docs/spec/product.md` (what the system is supposed to do)
3. `docs/github/projects-field-sync.md` (constraints you must not break)
4. `docs/adr/INDEX.md` (design decisions; read only what’s relevant)

## Authority and intent

pm-bot documentation follows a strict precedence model. If documents conflict, higher-precedence sources win.

1. **Canonical inputs** (`vendor/dotgithub/...`)
   - `vendor/dotgithub/ISSUE_TEMPLATE/*.yml`
   - `vendor/dotgithub/issue-templates-guide.md`
   - `vendor/dotgithub/project-field-sync.yml`
2. **Machine-readable contracts/schemas** (`pm_bot/schema/...`, `docs/contracts/...`)
   - `pm_bot/schema/work_item.schema.json`
   - all contract docs under `docs/contracts/`
3. **Behavioral specs** (`docs/spec/...`)
   - product and subsystem behavior definitions
4. **ADR decisions** (`docs/adr/INDEX.md` + tagged ADRs)
   - architecture and policy rationale that governs interpretation
5. **Status snapshot** (`STATUS.md`)
   - current repo health + compatibility snapshot aligned to higher sources
6. **Roadmaps** (`docs/roadmaps/...`) — planning only, never normative

Roadmaps MUST NOT override canonical inputs, contracts/schemas, or specs.

Roadmap defaults:
- Active near-term execution starts at [`docs/roadmaps/agent-roadmap-v3-near-term.md`](roadmaps/agent-roadmap-v3-near-term.md).
- Then progress to [`docs/roadmaps/agent-roadmap-v4-platform.md`](roadmaps/agent-roadmap-v4-platform.md), [`docs/roadmaps/agent-roadmap-v5-org-readiness.md`](roadmaps/agent-roadmap-v5-org-readiness.md), and [`docs/roadmaps/agent-roadmap-v6-multi-repo-orchestration.md`](roadmaps/agent-roadmap-v6-multi-repo-orchestration.md).
- Long-horizon ideas are separated in [`docs/roadmaps/future-roadmap.md`](roadmaps/future-roadmap.md) and are not default implementation sequencing.

## Quick links

- Product spec: [`docs/spec/product.md`](spec/product.md)
- Additional specs:
  - Graph/tree APIs: [`docs/spec/graph-api.md`](spec/graph-api.md)
  - Estimator v1: [`docs/spec/estimator.md`](spec/estimator.md)
  - Meta reporting: [`docs/spec/reporting.md`](spec/reporting.md)
  - Triage inbox: [`docs/spec/inbox.md`](spec/inbox.md)
- Contracts:
  - [`docs/contracts/report_ir_v1.md`](contracts/report_ir_v1.md)
  - [`docs/contracts/workgraph.md`](contracts/workgraph.md)
  - [`docs/contracts/changesets.md`](contracts/changesets.md)
  - [`docs/contracts/agent_run_spec.md`](contracts/agent_run_spec.md)
- GitHub integration:
  - Projects field sync: [`docs/github/projects-field-sync.md`](github/projects-field-sync.md)
  - Auth & tokens: [`docs/github/auth-and-tokens.md`](github/auth-and-tokens.md)
  - Tree & dependencies: [`docs/github/tree-and-dependencies.md`](github/tree-and-dependencies.md)
- Runbooks:
  - First human test: [`docs/runbooks/first-human-test.md`](runbooks/first-human-test.md)
- Maintenance:
  - [`docs/maintenance.md`](maintenance.md)

## Conventions

- Docs should be **actionable**: include examples and “how to test”.
- When a doc defines a contract, use **normative language**:
  - **MUST / MUST NOT** for hard requirements
  - **SHOULD / SHOULD NOT** for strong recommendations
  - **MAY** for optional behavior
- Prefer linking to the canonical file (schema/workflow/template) rather than copying it.
