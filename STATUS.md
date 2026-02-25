# Project Status (pm-bot)

> **Source of truth:** Update this file whenever behavior, tests, schemas, workflows, or canonical inputs change.
> **Agent rule:** Keep entries current. Add new `Scope` bullets for this change and remove stale scope bullets that no longer reflect repository state.
> **Date integrity rule:** Populate dates/times with runtime commands (for example `date -u`); never guess dates.

## Last updated
- Date: 2026-02-25
- Time (UTC): 09:00:22 UTC
- By: @openai-codex
- Scope: Completed roadmap v6 Track A (A1-A3) by adding context-pack and agent-run API client bindings, implementing operator UI flows for context-pack build plus agent-run propose/approve/claim/execute/cancel, enforcing execute-until-approved-and-claimed UI guards, adding reason-code centered error rendering, and extending UI tests for route coverage and Track A interactions.


---

## CI health checklist

| Check | Command | Status | Last run | Notes |
| --- | --- | --- | --- | --- |
| Tests | `pytest -q` | ✅ | 2026-02-25 | Covers v0-v5 behavior including runner lifecycle transitions, queue claim/retry/dead-letter semantics, adapter contract conformance, unified inbox contract/aggregation semantics, and HTTP contract behavior. |
| Lint | `ruff check .` | ✅ | 2026-02-25 | No lint violations. |
| Format | `ruff format .` | ✅ | 2026-02-25 | Formatting is stable. |
| Docs hygiene | `python scripts/docs_hygiene.py --check-links --check-contradictions --check-status-gates` | ✅ | 2026-02-25 | Validates local markdown links, contradiction-check workflow docs presence, and STATUS operability gates. |
| Package install | `pip install -e ".[dev]"` | ⬜ | — | Validate in clean environment if needed. |
| Docker Compose config | `docker compose config` | ✅ (CI) / ⚠️ (local env) | 2026-02-25 | Added CI validation job; local shell in this environment does not include Docker CLI. |

---

## Canonical contract status

### Inputs / schemas
- Templates snapshot: `vendor/dotgithub/ISSUE_TEMPLATE/*.yml`
- Templates guide: `vendor/dotgithub/issue-templates-guide.md`
- Projects sync workflow: `vendor/dotgithub/project-field-sync.yml`
- Work item schema: `pm_bot/schema/work_item.schema.json`

### Parser / renderer compatibility
- Required tracked headings and labels for project sync:
  `Area`, `Priority`, `Size`, `Estimate (hrs)`, `Risk`, `Blocked by`, `Actual (hrs)`
- Known compatibility note:
  Epic template currently uses `Size (Epic)`; parser compatibility shim is implemented and renderer normalizes to `Size`.

---

## Roadmap checklist (pm-bot)

### Issue template + schema pipeline
- [x] Canonical issue template snapshot vendorized under `vendor/dotgithub/ISSUE_TEMPLATE/`
- [x] Work item schema present (`pm_bot/schema/work_item.schema.json`)
- [x] Template map present (`pm_bot/schema/template_map.json`)
- [x] Template label/heading variants normalized in parser compatibility tests

### Parsing / rendering implementation
- [x] Issue body parsing module exists (`pm_bot/github/parse_issue_body.py`)
- [x] Body parser compatibility wrapper exists (`pm_bot/github/body_parser.py`)
- [x] Issue body rendering module exists (`pm_bot/github/render_issue_body.py`)
- [x] Template loading module exists (`pm_bot/github/template_loader.py`)

### Server / integration surface
- [x] API app entrypoint exists (`pm_bot/server/app.py`)
- [x] GitHub connector exists (`pm_bot/server/github_connector.py`)
- [x] Context packing + changesets plumbing exists (`pm_bot/server/context_pack.py`, `pm_bot/server/changesets.py`)
- [x] API contract/versioned milestones covered for v0-v2 local service methods

### Quality gates
- [x] Smoke test exists (`tests/test_smoke.py`)
- [x] Server test coverage exists (`tests/test_v1_server.py`)
- [x] Regression tests cover parser edge cases and v2 service behavior
- [x] Deterministic fixture-driven parse/render behavior tracked by tests

### Release readiness
- [x] Repository setup + command guidance documented in `AGENTS.md`
- [x] CHANGELOG policy documented and enforced
- [x] Versioning/release process documented

---

## Roadmap deliverables status (by version)

### v0 — Draft + Validate + CLI
- [x] Repo/package skeleton + CLI entrypoint (`pm_bot/cli.py`, `pyproject.toml`)
- [x] Deterministic body parsing + rendering modules (`pm_bot/github/parse_issue_body.py`, `pm_bot/github/render_issue_body.py`)
- [x] Template loading and schema artifacts (`pm_bot/github/template_loader.py`, `pm_bot/schema/*.json`)
- [x] Basic smoke coverage (`tests/test_smoke.py`)
- [x] `pm parse --url` support

### v1 — Safe write orchestrator + context packs
- [x] Server app + API surface (`pm_bot/server/app.py`)
- [x] SQLite backing store for work items, changesets, approvals, audit trail (`pm_bot/server/db.py`)
- [x] Guardrailed write connector + approval flow (`pm_bot/server/github_connector.py`, `pm_bot/server/changesets.py`)
- [x] Webhook ingestion + read/list issue connectors

### v2 — Tree/graph UI + estimator + meta reports
- [x] Graph/tree API service methods (`pm_bot/server/graph.py`, `pm_bot/server/app.py`)
- [x] Estimator v1 implementation (bucketed P50/P80 with fallback order and snapshots) (`pm_bot/server/estimator.py`)
- [x] Meta reporting output generation (`pm_bot/server/reporting.py`, `reports/`)
- [x] Safety incident tracking for denied writes (`changeset_denied` audit events)

### Stage progress — N1/N2/N3
- [x] N1 / v3 near-term complete (`docs/roadmaps/agent-roadmap-v3-near-term.md`)
- [x] N2 / v4 platform reliability complete (`docs/roadmaps/agent-roadmap-v4-platform.md`)
- [x] N3 / v5 org readiness started (`docs/roadmaps/agent-roadmap-v5-org-readiness.md`)
- [x] v6 roadmap decomposition published (`docs/roadmaps/agent-roadmap-v6-multi-repo-orchestration.md`, `docs/ROADMAP_V6_CHECKLIST.md`)

### Future roadmap (long-horizon, non-default)
- [ ] Future SaaS shape execution intentionally deferred (`docs/roadmaps/future-roadmap.md`)


## v4 ship readiness snapshot
- Done: Policy reason normalization, idempotency-key reuse, bounded retry/dead-letter handling, operation metrics aggregation, and run-id correlation across changesets/webhooks/reports.
- Remaining: N3 / v5 org-readiness stage only; v3 near-term and v4 platform scopes are complete.
- End-to-end demo (local):
  1) `pytest -q`
  2) Propose + approve a normal changeset (`create_issue`) and verify `changeset_applied`.
  3) Propose + approve with `_transient_failures` to validate retries and dead-letter path.
  4) Ingest a webhook and generate a report with shared `run_id`; verify correlated audit events.
