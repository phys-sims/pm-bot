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
| 11 | v3 | Docs authority pass + active stage defaults (criteria: docs links validated by `python scripts/docs_hygiene.py --check-links` in CI + docs hygiene tests) | agent | ☑ done | archived-history | none |
| 12 | v3 | ADR index/path hygiene and contradiction cleanup (criteria: contradiction-check workflow documented in `docs/maintenance.md` and checked by `--check-contradictions`) | agent | ☑ done | archived-history | none |
| 13 | v3 | Operability gates reflected in STATUS + docs (criteria: STATUS command gates + docs hygiene CI/docs matrix coverage + explicit tests) | agent | ☑ done | archived-history | none |
| 14 | v4 | Policy decision normalization with reason codes | agent | ☑ done | archived-history | none |
| 15 | v4 | Queue/retry/idempotency hardening | agent | ☑ done | archived-history | none |
| 16 | v4 | Observability/SLO instrumentation and correlation IDs | agent | ☑ done | archived-history | none |
| 17 | v4 | Runbook completion for incident classes | agent | ☑ done | archived-history | none |

## Top remaining work (highest leverage)
1. Begin N3 / v5 org readiness sequencing once human sign-off confirms v4 acceptance.
2. Expand reliability metrics export to dashboard/report rollups.
3. Add production-grade backoff jitter controls when moving beyond in-memory connector.
4. Add webhook drift auto-remediation tooling from runbook actions.
5. Capture human validation evidence for v4 runbook scenarios.
