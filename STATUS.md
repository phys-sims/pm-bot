# Project Status (pm-bot)

> **Source of truth:** Update this file whenever behavior, tests, schemas, workflows, or canonical inputs change.
> **Agent rule:** Keep entries current. Add new `Scope` bullets for this change and remove stale scope bullets that no longer reflect repository state.
> **Date integrity rule:** Populate dates/times with runtime commands (for example `date -u`); never guess dates.

## Last updated
- Date: 2026-02-26
- Time (UTC): 03:47:45 UTC
- By: @openai-codex
- Scope: Follow-up hygiene fix: applied `ruff format` to `scripts/docs_hygiene.py`, re-ran lint/docs-hygiene/doc-command tests, and confirmed the strict 3-level docs entrypoint enforcement remains green.

---

## CI health checklist

| Check | Command | Status | Last run | Notes |
| --- | --- | --- | --- | --- |
| Tests | `pytest -q` | ✅ | 2026-02-26 | Core suites cover parser/rendering, server behavior, contracts, and docs hygiene.
| Lint | `ruff check .` | ✅ | 2026-02-26 | No lint violations.
| Format | `ruff format .` | ✅ | 2026-02-26 | Formatting is stable.
| Docs hygiene | `python scripts/docs_hygiene.py --check-links --check-contradictions --check-status-gates` | ✅ | 2026-02-26 | Validates markdown links, docs-governance workflow references, and entrypoint boundary gates.
| Package install | `pip install -e ".[dev]"` | ⬜ | — | Validate in clean environment if needed.
| Docker Compose config | `docker compose config` | ✅ (CI) / ⚠️ (local env) | 2026-02-25 | CI validates compose; local shell in this environment may not include Docker CLI.

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

## Current-state deltas

- Documentation entrypoint split is now explicit and enforced via docs governance and hygiene checks:
  - `README.md`: orientation + install/run + links only.
  - `docs/README.md`: canonical docs IA + precedence + ownership.
  - `STATUS.md`: runtime health + current-state updates only.
