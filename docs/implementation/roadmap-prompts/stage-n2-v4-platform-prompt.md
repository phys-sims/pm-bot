# Prompt Package — Stage N2 (v4 Platform Reliability)

Generate/update `docs/roadmaps/agent-roadmap-v4-platform.md`.

## Mission
Define single-tenant platform reliability and policy maturity work: policy engine hardening, queue/retry/idempotency improvements, and observability/runbook completeness.

## Mandatory sources to cite
- `STATUS.md`
- `docs/adr/INDEX.md`
- `docs/contracts/changesets.md`
- `docs/spec/product.md`
- relevant ops/safety/auth ADRs

## Constraints
- Preserve approval-gated writes and deterministic behavior.
- Keep scope single-tenant.
- Use measurable reliability KPIs.

## Non-goals
- Multi-tenant control plane, billing, external connector expansion.

## Deliverables
- Stage boundary section (in/out/dependencies/exit criteria/owner type).
- 1–2 day tasks with explicit file targets.
- Reliability KPIs and failure-budget expectations.
- Rollout/rollback path using flags or phased deployment.

## Required checks
- `pytest -q`
- `ruff check .`
- `ruff format .`
- reliability-focused tests (queue/retry/idempotency)

## Additional requirements
- Update `STATUS.md` roadmap section with N2 sequencing after N1.
- Include citations for each policy/reliability requirement.
