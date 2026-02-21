# Agent Roadmap v2 — Tree/Graph UI + Estimator v1 + Meta Reports
_Date: 2026-02-21_

## Mission
Make this “feel like a product” for personal use:
- A tree/graph visualization of work across repos
- A basic estimator that learns from actuals
- A meta-reporting system that tells you whether agents are helping or hurting

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

2) **Estimator v1 (distributional)**
- Use historical items with `Actual (hrs)` populated.
- Bucket by: (type, area, size)
- Compute P50 and P80.
- Display:
  - predicted P50/P80
  - how many samples in bucket
  - warning when bucket is sparse (fallback to broader bucket)

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

---

## Implementation tasks (Codex-sized)
### Task A: graph data model + API
- Add endpoints:
  - `/graph/tree?root=<issue>`
  - `/graph/deps?area=...`
- Include pagination/lazy loading for large trees.

### Task B: UI Tree view
- Render expandable nodes
- Show badges: priority, risk, status, estimator P50/P80
- “Draft child issue” button that creates a changeset (still approval-gated)

### Task C: estimator baseline pipeline
- Job to compute bucket stats nightly
- Store in `estimate_snapshots` table
- Backtest metrics saved for reports

### Task D: reporting engine
- Generate a weekly report:
  - wins (time saved proxy)
  - failure clusters (which headings fail, which areas cause churn)
  - recommended template improvements

---

## Acceptance criteria
- You can open the UI and see your Epics as trees.
- Estimator produces P50/P80 and shows calibration coverage on history.
- A weekly report is generated automatically.

---

## Template changes that help v2 most
- Ensure `Actual (hrs)` exists and is sometimes filled in (even approximate).
- Normalize Epic size so estimator buckets work cleanly.
