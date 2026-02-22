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

