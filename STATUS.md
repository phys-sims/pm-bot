# Project Status (pm-bot)

> **Source of truth:** Update this file whenever behavior, tests, schemas, workflows, or canonical inputs change.
> **Agent rule:** Keep entries current. Add new `Scope` bullets for this change and remove stale scope bullets that no longer reflect repository state.
> **Date integrity rule:** Populate dates/times with runtime commands (for example `date -u`); never guess dates.

## Last updated
- Date: 2026-02-22
- By: @openai-codex
- Scope: Added explicit date-integrity guidance requiring runtime date/time commands for `STATUS.md` updates.
- Scope: Added roadmap release-language checklist section to keep release communication consistent and auditable.

---

## CI health checklist

| Check | Command | Status | Last run | Notes |
| --- | --- | --- | --- | --- |
| Tests | `pytest -q` | ⬜ | — | Run locally/CI and update this row after changes. |
| Lint | `ruff check .` | ⬜ | — | Keep green before merge. |
| Format | `ruff format .` | ⬜ | — | Ensure formatting is stable. |
| Package install | `pip install -e ".[dev]"` | ⬜ | — | Validate environment bootstrap path. |

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
  Epic template currently uses `Size (Epic)`; parser/template alignment should converge on `Size` or maintain a clear compatibility shim.

---

## Roadmap checklist (pm-bot)

### Issue template + schema pipeline
- [x] Canonical issue template snapshot vendorized under `vendor/dotgithub/ISSUE_TEMPLATE/`
- [x] Work item schema present (`pm_bot/schema/work_item.schema.json`)
- [x] Template map present (`pm_bot/schema/template_map.json`)
- [ ] Confirm all template label/heading variants are normalized in parser compatibility tests

### Parsing / rendering implementation
- [x] Issue body parsing module exists (`pm_bot/github/parse_issue_body.py`)
- [x] Body parser compatibility wrapper exists (`pm_bot/github/body_parser.py`)
- [x] Issue body rendering module exists (`pm_bot/github/render_issue_body.py`)
- [x] Template loading module exists (`pm_bot/github/template_loader.py`)

### Server / integration surface
- [x] API app entrypoint exists (`pm_bot/server/app.py`)
- [x] GitHub connector exists (`pm_bot/server/github_connector.py`)
- [x] Context packing + changesets plumbing exists (`pm_bot/server/context_pack.py`, `pm_bot/server/changesets.py`)
- [ ] Track API contract/versioning milestones for public endpoints

### Quality gates
- [x] Smoke test exists (`tests/test_smoke.py`)
- [x] Server test coverage exists (`tests/test_v1_server.py`)
- [ ] Expand regression tests for parser edge cases from template evolution
- [ ] Add/track deterministic fixture set for template roundtrip behavior

### Release readiness
- [x] Repository setup + command guidance documented in `AGENTS.md`
- [ ] CHANGELOG policy documented and enforced
- [ ] Versioning/release process documented

---


## Roadmap release-language checklist

Use this checklist when updating roadmap/release notes so language stays consistent and testable.

- [ ] Explicitly state release phase using one of: `planned`, `in progress`, `blocked`, `ready`, `released`.
- [ ] Tie each release claim to concrete artifacts (PRs, docs, tests, schemas, or workflows).
- [ ] Avoid ambiguous wording like "almost done"; replace with measurable criteria or checklist status.
- [ ] Include compatibility impact statements when changing headings/labels parsed by automation.
- [ ] Include validation evidence (tests/check commands) for any "ready" or "released" claim.
- [ ] Remove superseded release-status bullets so stale roadmap statements do not persist.

---

## Known issues
- Stale status scope entries can accumulate if contributors append without pruning obsolete scopes.

---

## Next actions
- [ ] Run lint + tests and fill CI status rows with latest run date and notes.
- [ ] Add parser regression tests covering `Size (Epic)` compatibility strategy.
- [ ] Keep this tracker synchronized with roadmap/spec updates in `docs/roadmaps/`.