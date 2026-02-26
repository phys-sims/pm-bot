# Prompt Package — Stage N3 (v5 Org Readiness)

Generate/update `docs/roadmaps/agent-roadmap-v5-org-readiness.md`.

## Mission
Define org-readiness prerequisites without full SaaS billing: tenant-aware data model prep, auth boundary prep, onboarding scaffolding, and compliance/audit posture upgrades.

## Mandatory sources to cite
- `STATUS.md`
- `docs/adr/INDEX.md`
- `docs/contracts/*.md` (especially changesets/agent run contracts)
- `docs/spec/product.md`
- relevant auth/safety/ops ADRs

## Constraints
- Preserve existing single-tenant operation by default.
- Keep tasks staged and reversible.
- Require measurable onboarding/compliance KPIs.

## Non-goals
- Full billing, marketplace monetization, production-grade multi-tenant control plane.

## Deliverables
- Stage boundary section (in/out/dependencies/exit criteria/owner type).
- 1–2 day implementation slices with file targets and checks.
- KPI section for tenant context, onboarding readiness, and audit coverage.
- Rollout/rollback plan and acceptance criteria.

## Required checks
- `pytest -q`
- `ruff check .`
- `ruff format .`
- auth/audit/onboarding targeted tests

## Additional requirements
- Update `STATUS.md` roadmap section to include N3 planned-after N2.
- Include citations for each contract/auth/compliance claim.
