# Roadmap v1→v4 Unified Execution Checklist

This checklist unifies deliverables across v1, v2, v3 near-term, and v4 platform.

Legend: `☑ done`, `◐ in progress`, `☐ pending`.

| Order | Stage | Item | Owner | Status | PR link | Blockers |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | v1 | Server + DB orchestration primitives | agent | ☑ done | n/a (pre-existing) | none |
| 2 | v1 | GitHub connector with approval-gated writes | agent | ☑ done | n/a (pre-existing) | none |
| 3 | v1 | Webhook ingestion to canonical work items | agent | ☑ done | n/a (pre-existing) | none |
| 4 | v1 | Changeset propose/approve/apply workflow | agent | ☑ done | n/a (pre-existing) | none |
| 5 | v1 | Context pack builder with deterministic hashing | agent | ☑ done | n/a (pre-existing) | none |
| 6 | v1 | Minimal approvals surface + audit trail | agent | ☑ done | n/a (pre-existing) | none |
| 7 | v2 | Tree/dependency graph services | agent | ☑ done | n/a (pre-existing) | none |
| 8 | v2 | Estimator v1 with deterministic fallback path | agent | ☑ done | n/a (pre-existing) | none |
| 9 | v2 | Weekly meta reporting output | agent | ☑ done | n/a (pre-existing) | none |
| 10 | v2 | Data quality checks for canonical headings/labels | agent | ☑ done | n/a (pre-existing) | none |
| 11 | v3 | Docs authority pass + active stage defaults | agent | ◐ in progress | (this PR) | continue hardening and link validation |
| 12 | v3 | ADR index/path hygiene and contradiction cleanup | agent | ◐ in progress | (this PR) | complete contradiction-check workflow |
| 13 | v3 | Operability gates reflected in STATUS + docs | agent | ◐ in progress | (this PR) | continue with CI/report hygiene checks |
| 14 | v4 | Policy decision normalization with reason codes | agent | ◐ in progress | (this PR) | extend matrix coverage + spec wording |
| 15 | v4 | Queue/retry/idempotency hardening | agent | ☐ pending | — | design + implementation not started |
| 16 | v4 | Observability/SLO instrumentation and correlation IDs | agent | ☐ pending | — | metrics/tracing surface not implemented |
| 17 | v4 | Runbook completion for incident classes | agent | ☐ pending | — | runbook expansion not started |

## Top remaining work (highest leverage)
1. Finish v4 policy normalization (reason-code matrix and docs/spec linkage).
2. Add idempotency keys + bounded retry behavior for writes.
3. Add reliability tests for retry and partial-failure convergence.
4. Add observability counters/traces tied to run/changeset IDs.
5. Complete runbooks for retry storms, webhook drift, and denial spikes.
