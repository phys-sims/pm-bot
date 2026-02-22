# Project Status (pm-bot)

> **Source of truth:** Update this file whenever behavior, tests, schemas, workflows, or canonical inputs change.
> **Agent rule:** Keep entries current. Add new `Scope` bullets for this change and remove stale scope bullets that no longer reflect repository state.
> **Date integrity rule:** Populate dates/times with runtime commands (for example `date -u`); never guess dates.

## Last updated
- Date: 2026-02-22
- Time (UTC): 06:12:05 UTC
- By: @openai-codex
- Scope: Reclassified former `agent-roadmap-v3.md` as `docs/roadmaps/future-roadmap.md` and added an explicit long-horizon/non-default sequencing banner.
- Scope: Added new executable stage roadmaps for N1 (`agent-roadmap-v3-near-term.md`), N2 (`agent-roadmap-v4-platform.md`), and N3 (`agent-roadmap-v5-org-readiness.md`) with scope boundaries, KPIs, checks, and rollout/rollback guidance.
- Scope: Added reusable roadmap generation prompt template plus per-stage prompt packages and updated docs navigation (`README.md`, `docs/README.md`, `docs/roadmaps/human-roadmap.md`, `docs/maintenance.md`) to default agents/humans to near-term sequencing.


---

## CI health checklist

| Check | Command | Status | Last run | Notes |
| --- | --- | --- | --- | --- |
| Tests | `pytest -q` | ✅ | 2026-02-22 | Covers v0 parse/render and v1/v2 server behavior. |
| Lint | `ruff check .` | ✅ | 2026-02-22 | No lint violations. |
| Format | `ruff format .` | ✅ | 2026-02-22 | Formatting is stable. |
| Package install | `pip install -e ".[dev]"` | ⬜ | — | Validate in clean environment if needed. |

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

### Active sequencing — N1/N2/N3
- [ ] N1 / v3 near-term execution started (`docs/roadmaps/agent-roadmap-v3-near-term.md`)
- [ ] N2 / v4 platform reliability started (`docs/roadmaps/agent-roadmap-v4-platform.md`)
- [ ] N3 / v5 org readiness started (`docs/roadmaps/agent-roadmap-v5-org-readiness.md`)

### Future roadmap (long-horizon, non-default)
- [ ] Future SaaS shape execution intentionally deferred (`docs/roadmaps/future-roadmap.md`)
