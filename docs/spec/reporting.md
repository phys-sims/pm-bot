# Meta reporting specification

Meta reports answer: “Are agents and automation helping or hurting?”

They should be:

- **regular** (weekly)
- **actionable** (recommendations tied to metrics)
- **low-effort to read** (one markdown file)

## Outputs

- Weekly markdown report committed under `reports/`
- Optional UI dashboard view (later)

## Minimum metrics

### Draft quality

- Draft acceptance rate:
  - % of drafted issues that were published without edits
- Validator failure rate (per template type)
- Average # of human edits per published draft (proxy for churn)

### Estimation quality

- Calibration:
  - % of actuals ≤ predicted P80 (target ≥ 80%)
- Bucket health:
  - sample counts per (type, area, size)
  - top sparse buckets where fallback happens frequently

### Safety and policy

- blocked write attempts
- changeset denials (policy denies, missing approvals)
- agent run denials (token spend blocked)
- anomaly counts (unexpected repo targets, forbidden ops)

### Data quality

- % missing `Area`
- % missing `Size`
- % missing `Actual (hrs)` for closed items
- top offenders by repo/template type

## Report structure (recommended)

```markdown
# Weekly pm-bot report — YYYY‑MM‑DD

## Summary
- Wins:
- Pain points:
- Recommended actions (top 3):

## Drafting quality
- Acceptance rate:
- Validator failures:

## Estimation
- P80 coverage:
- Sparse buckets:

## Safety incidents
- Denied changesets:
- Denied agent runs:

## Data quality
- Missing fields:
- Remediation suggestions:

## Appendix
- Snapshot IDs:
- Top failing headings:
```

## Determinism and traceability

Every report MUST include:

- report generation timestamp
- snapshot IDs used (estimator snapshot, audit snapshot)
- run IDs used to correlate ingestion/changesets/report generation events
- counts and sample sizes for all metrics

## Remediation suggestions (examples)

Reports should propose concrete actions like:

- “Add `Actual (hrs)` prompt to Feature/Task templates”
- “Normalize Epic size heading to `Size`”
- “Create `needs-human` label convention for missing Area/Priority”

## References

- Roadmap v2 (meta reports)
- `docs/contracts/changesets.md` (audit events)
- `docs/spec/estimator.md` (estimation metrics)



## Org-sensitive safety reporting (v5)

Weekly reporting now includes org-sensitive operational taxonomy counters:

- `auth_context_denials`: requests denied by org/install context validation.
- `org_sensitive_operations`: aggregate of proposed/applied changesets and context denials.

These counters complement existing `changeset_denied` and `changeset_dead_lettered` safety metrics.

## Multi-agent audit operations surface (v6 / Track D)

The server exposes audit-first operations endpoints for deterministic chain triage:

- `GET /audit/chain`
  - filters: `run_id`, `event_type`, `repo`, `actor`, `start_at`, `end_at`
  - pagination: `limit` (bounded to 1..500), `offset`
  - response: `audit_chain/v1` with stable ordering by event ID ascending.
- `GET /audit/rollups`
  - optional filter: `run_id`
  - response: `audit_rollups/v1` summary with sample size, completion rate,
    retry/dead-letter/denial counts, queue age mean, and top reason/repo concentration slices.
- `GET /audit/incident-bundle`
  - optional filters: `run_id`, `actor`
  - response: `incident_bundle/v1` containing run metadata, runbook hooks,
    a bounded audit chain snapshot, and rollup metrics.

These routes are read-only and preserve existing approval semantics for any writes.
