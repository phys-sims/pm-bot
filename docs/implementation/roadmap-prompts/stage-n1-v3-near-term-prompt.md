# Prompt Package — Stage N1 (v3 Near-Term Execution)

Generate/update `docs/roadmaps/agent-roadmap-v3-near-term.md`.

## Mission
Define an immediately executable roadmap for post-v2 hardening: documentation authority consolidation, ADR index/path consistency, contract/spec de-duplication, and operational quality gates.

## Mandatory sources to cite
- `STATUS.md`
- `docs/adr/INDEX.md`
- Relevant `docs/contracts/*.md`
- Relevant `docs/spec/*.md`
- `docs/README.md`

## Constraints
- Keep canonical headings/labels compatible with GitHub Projects sync.
- Keep tasks in deterministic 1–2 day slices.
- Include measurable KPIs and explicit test commands.

## Non-goals
- Multi-tenant architecture, billing, SaaS commercialization.

## Deliverables
- Stage boundary: in scope, out of scope, dependencies, exit criteria, owner type.
- Task backlog with file targets and per-task validation commands.
- KPI table with thresholds.
- Rollout/rollback and acceptance criteria.

## Required checks
- `pytest -q`
- `ruff check .`
- `ruff format .`

## Additional requirements
- Update `STATUS.md` roadmap section to show N1 as active stage.
- Include citations to every contract/spec/ADR claim.
