# Agent Roadmap v4 Platform — Single-tenant Reliability + Policy Maturity
_Date: 2026-02-22_

## Stage boundary
### In scope
- Policy engine hardening for single-tenant write safety and approval semantics.
- Queueing/retry/idempotency improvements in orchestration paths.
- Observability upgrades (structured metrics, traces/log correlation, runbook completeness).
- Reliability test harnesses for failure/retry paths.

### Out of scope
- True multi-tenant isolation, tenant billing, or org marketplace flows.
- Non-GitHub connector expansion.
- Full enterprise IAM federation.

### Dependencies
- v3 near-term completion (docs/contracts/spec alignment baseline).
- ADR guidance for safety/auth/ops/contracts domains.
- Existing server components (`changesets`, `github_connector`, `context_pack`, reporting).

### Exit criteria
- Idempotent retry behavior is documented and tested for critical writes.
- Policy decisions are auditable with deterministic deny/approve reasons.
- Runbooks cover normal ops + key incident classes.

### Owner type
- Mixed (agent implementation, human sign-off on policy semantics and risk thresholds).

## Mission
Increase platform reliability and safety maturity so single-tenant deployments operate predictably under retries, outages, and high-change workloads.

## Codex-sized implementation slices (1–2 days each)
1. **Policy decision normalization**
   - Encode deterministic allow/deny reason codes.
   - Add tests for policy matrix edge cases.
2. **Queue/retry/idempotency hardening**
   - Introduce idempotency keys for write operations.
   - Add bounded retries with backoff and dead-letter reporting.
3. **Observability and SLO instrumentation**
   - Track latency/success/failure by operation family.
   - Correlate run IDs across ingestion, changesets, and reporting.
4. **Runbook completion pass**
   - Incident playbooks for retry storms, webhook drift, and policy-denial spikes.

## KPIs
- ≥99% successful completion for retry-eligible operations within configured retry budget.
- 100% of denied writes include machine-readable reason code.
- Mean time to triage (MTTT) incidents reduced with runbook-backed checks.

## Required checks
- `pytest -q`
- `ruff check .`
- `ruff format .`
- targeted reliability tests for retry/idempotency paths

## Rollout and rollback
- Rollout behind feature flags for retry/policy changes.
- Rollback by disabling new retry/policy toggles and reverting migration-free changes.

## Acceptance criteria
- Reliability behavior is deterministic and covered by tests.
- Policy engine behavior is documented in specs/contracts and reflected in status health.
- Runbooks map directly to emitted observability signals.
