# Agent Roadmap v2 — Tree/Graph UI + Estimator v1 + Meta Reports
_Date: 2026-02-21_

## Mission
Make this “feel like a product” for personal use:
- A tree/graph visualization of work across repos
- A basic estimator that learns from actuals
- A meta-reporting system that tells you whether agents are helping or hurting

## Constraints
- Preserve compatibility with existing GitHub issue templates and Projects sync behavior.
- Keep estimation deterministic and explainable (no opaque model in v2).
- Keep all write actions approval-gated (same safety model as v1).
- Support gradual rollout: UI/estimator should work even when data is sparse or partially missing.

## Inputs you must use
- Templates snapshot: `vendor/dotgithub/ISSUE_TEMPLATE/*.yml`
- Templates guide: `vendor/dotgithub/issue-templates-guide.md`
- Projects sync workflow: `vendor/dotgithub/project-field-sync.yml`
- Canonical schema: `pm_bot/schema/work_item.schema.json`

## Non-goals (v2)
- No multi-tenant or billing functionality (belongs to v3).
- No advanced Bayesian/hierarchical estimator (baseline only in v2).
- No fully automated writes without human approval.

---

## Deliverables
1) **Tree + dependency graph UI**
- Implement a web UI (React/Next or simple SPA).
- Views:
  - Tree (epic→feature→task) with expand/collapse
  - Dependency overlay (blocked-by edges)
  - Roll-up progress (closed children / total)
- Data sources:
  - Prefer GitHub sub-issues if available.
  - Fall back to parsing checklists in Epic/Feature templates.
  - Show source confidence (sub-issue vs checklist-derived).

2) **Estimator v1 (distributional)**
- Use historical items with `Actual (hrs)` populated.
- Bucket by: (type, area, size)
- Compute P50 and P80.
- Display:
  - predicted P50/P80
  - how many samples in bucket
  - warning when bucket is sparse (fallback to broader bucket)
  - provenance for fallback path (exact bucket → broader bucket → global)

3) **Meta reports on agent usage**
Metrics (minimum):
- Draft acceptance rate (published without edits)
- Validator failure rate (per template type)
- Average # of human edits per published draft
- Estimation calibration:
  - % of actuals ≤ P80 (target ≥ 80%)
- Safety incidents:
  - blocked write attempts
  - policy denials

Outputs:
- weekly markdown report committed to `pm-bot/reports/`
- optional dashboard page

4) **Data quality feedback loop**
- Report missing/invalid values for estimator-critical fields:
  - `Area`, `Size`, `Actual (hrs)`, closure status
- Surface top offenders by template type and repository.
- Include concrete remediation suggestions (template text or workflow changes).

---

## Implementation tasks (Codex-sized)
### Task A: graph data model + API
- Add endpoints:
  - `/graph/tree?root=<issue>`
  - `/graph/deps?area=...`
- Include pagination/lazy loading for large trees.
- Include edge typing (`parent_child`, `blocked_by`, `related`) and provenance metadata.

### Task B: UI Tree view
- Render expandable nodes
- Show badges: priority, risk, status, estimator P50/P80
- “Draft child issue” button that creates a changeset (still approval-gated)
- Add quick filters (area/type/status) and node search.

### Task C: estimator baseline pipeline
- Job to compute bucket stats nightly
- Store in `estimate_snapshots` table
- Backtest metrics saved for reports
- Deterministic fallback order:
  1. (type, area, size)
  2. (type, area)
  3. (type)
  4. global
- Persist sample counts and quantile method used.

### Task D: reporting engine
- Generate a weekly report:
  - wins (time saved proxy)
  - failure clusters (which headings fail, which areas cause churn)
  - recommended template improvements

### Task E: scheduler + retention
- Add scheduled jobs for:
  - nightly estimator snapshot
  - weekly report generation
- Add retention policy for raw metrics snapshots (for example 180 days raw, long-term aggregates retained).

### Task F: observability + safety checks
- Instrument report/estimator pipelines with run IDs and duration metrics.
- Log and report policy denials and blocked operations consistently with v1 audit model.
- Fail closed on missing approvals for draft-child actions.

---

## Acceptance criteria
- You can open the UI and see your Epics as trees.
- Estimator produces P50/P80 and shows calibration coverage on history.
- A weekly report is generated automatically.
- UI shows dependency edges and provenance for hierarchy derivation.
- Sparse buckets are surfaced with explicit fallback explanation and sample counts.
- Report includes at least one actionable recommendation section tied to measurable failures.

## Guardrails (must implement)
- Never mutate issues/projects directly from UI actions without creating a changeset.
- Record estimator version + fallback rule in each prediction shown to users.
- Exclude incomplete/invalid `Actual (hrs)` values from quantile computation and report exclusions.
- Keep heading labels compatible with Projects sync expectations (`Area`, `Priority`, `Size`, `Estimate (hrs)`, `Risk`, `Blocked by`, `Actual (hrs)`).

---

## Template changes that help v2 most
- Ensure `Actual (hrs)` exists and is sometimes filled in (even approximate).
- Normalize Epic size so estimator buckets work cleanly.
