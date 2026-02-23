# Weekly pm-bot report — 2026-02-23

## Summary
- Wins:
  - Draft acceptance held at 50.00% across 2 proposed changesets.
  - P80 coverage is 50.00% over 2 comparable closed items.
- Pain points:
  - Missing `Area` on 1 of 3 items.
  - Missing `Actual (hrs)` on 1 of 3 closed items.
- Recommended actions (top 3):
  1. Add explicit `Actual (hrs)` prompts in templates for close-out workflows.
  2. Require `Area` and `Size` before publish in validator checks.
  3. Increase estimator bucket samples for sparse buckets listed below.

## Drafting quality
- Acceptance rate: 50.00% (sample=2).
- Validator failures: 100.00% (count=2, sample=2).
- Average # of human edits per published draft: 0.00 (sample=1).

## Estimation
- P80 coverage: 50.00% (covered=1, sample=2).
- Snapshot bucket count: 2.
- Sparse buckets:
  - task|platform|S (sample_count=2)

## Safety incidents
- Denied changesets: 1 (blocked write attempts=1, sample=5).
- Denied agent runs: 0 (sample=5).
- Dead-lettered changesets: 1 (sample=5).
- Anomaly counts: 0 (sample=5).

## Data quality
- Missing `Area`: 33.33% (count=1, sample=3).
- Missing `Size`: 33.33% (count=1, sample=3).
- Missing `Actual (hrs)` for closed items: 33.33% (count=1, sample=3).
- Top offenders by template type:
  - task (missing=1, sample=1)

## Appendix
- Snapshot IDs: estimator=[1, 2], audit=[1, 5]
- Report generation timestamp: 2026-02-23T12:00:00+00:00
- Run IDs: ['run-1', 'run-2']
- Snapshot sample sizes: audit_events=5, work_items=3, estimator_buckets=2
