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

## LLM feature performance
- Recommendation acceptance rate: 50.00% (accepted=1, sample=2).
- Override/edit rate before approval: 50.00% (count=1, sample=2).
- False-positive rate (rejected proposals): 50.00% (rejected=1, sample=2).
- Downstream outcomes: avg lead time=24.00h (sample=1), reopened tasks=1, blocker resolutions=1.
- Per-capability metrics:
  - issue_replanner: acceptance=0.00% (accepted=0, sample=1), override/edit=100.00% (count=1, sample=1), false-positive=100.00% (rejected=1, sample=1), avg lead time=0.00h (sample=0), reopened=1, blocker resolutions=0
  - report_ir_draft: acceptance=100.00% (accepted=1, sample=1), override/edit=0.00% (count=0, sample=1), false-positive=0.00% (rejected=0, sample=1), avg lead time=24.00h (sample=1), reopened=0, blocker resolutions=1

## Estimation
- P80 coverage: 50.00% (covered=1, sample=2).
- Snapshot bucket count: 2.
- Sparse buckets:
  - task|platform|S (sample_count=2)
- Excluded historical samples: total=0 reasons={}.

## Safety incidents
- Denied changesets: 1 (blocked write attempts=1, sample=10).
- Denied agent runs: 0 (sample=10).
- Dead-lettered changesets: 1 (sample=10).
- Auth context denials: 0 (sample=10).
- Org-sensitive operation events: 3 (sample=10).
- Anomaly counts: 0 (sample=10).

## Data quality
- Missing `Area`: 33.33% (count=1, sample=3).
- Missing `Size`: 33.33% (count=1, sample=3).
- Missing `Actual (hrs)` for closed items: 33.33% (count=1, sample=3).
- Top offenders by template type:
  - task (missing=1, sample=1)

## Appendix
- Snapshot IDs: estimator=[1, 2], audit=[1, 10]
- Report generation timestamp: 2026-02-23T12:00:00+00:00
- Run IDs: ['run-1', 'run-2']
- Context packs built: count=0 hashes=[]
- Snapshot sample sizes: audit_events=10, work_items=3, estimator_buckets=2
