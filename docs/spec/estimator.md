# Estimator v1 specification

pm-bot’s estimator is designed to be:

- **deterministic**
- **explainable**
- **useful even with sparse data**

It uses historical `Actual (hrs)` data to produce a P50 and P80 estimate for new work items.

## Inputs

Estimator v1 depends on these fields being present and clean:

- `type` (feature/task/bug/…)
- `area`
- `size`
- `actual_hrs` (for historical training samples)

These fields map to GitHub issue headings and/or labels, and are tracked for Projects sync.

## Bucketing and fallback

Estimator v1 buckets historical samples by:

1. `(type, area, size)`
2. `(type, area)`
3. `(type)`
4. `global`

When estimating a new item, it chooses the most specific bucket with enough samples and falls back deterministically.

### Minimum sample thresholds (recommended)

- A bucket SHOULD have at least N samples to be considered reliable.
  - Example: `N = 5`

If a bucket is sparse, the estimator MUST:

- fall back to the next broader bucket
- record the fallback path and sample counts

## Quantiles

For each bucket, compute:

- P50 (median)
- P80 (80th percentile)

Implementation MUST be deterministic:

- use a fixed quantile method across runs
- store the method used in snapshot metadata

## Data exclusions

Historical samples MUST be excluded if:

- `actual_hrs` is missing
- `actual_hrs` is non-numeric or <= 0
- (optional) `actual_hrs` is implausibly large and marked as an outlier by a deterministic rule

Exclusions SHOULD be reported in meta reports.

## Outputs

For a given work item, the estimator should return:

- `p50_hrs`
- `p80_hrs`
- `bucket_used` (which bucket level)
- `sample_count`
- `fallback_path` (exact → broader → …)
- `snapshot_id` / `estimator_version`

This output should be displayable in:

- UI (tree view nodes)
- reports
- API responses

## Calibration metric

A key metric is P80 coverage:

> % of historical items where `actual_hrs <= predicted_p80_hrs`

Target (recommended baseline):

- ≥ 80% coverage

This is not guaranteed in small datasets; report sample sizes and confidence.

## Storage and scheduling

Recommended:

- nightly job computes bucket statistics
- store in an `estimate_snapshots` table
- keep retention policy for raw snapshots (e.g., 180 days)

## Human guidance

Estimator quality depends on data hygiene.

To improve estimates:

- fill `Actual (hrs)` when closing tasks (rough is fine)
- keep `Area` and `Size` consistent (avoid “misc” overuse)

## References

- See roadmap v2 for the intended estimator behavior.
- See `docs/github/projects-field-sync.md` for how these fields are populated.

