# Project Status (pm-bot)

> **Source of truth:** Update this file whenever behavior, tests, schemas, workflows, or canonical inputs change.
> **Agent rule:** Keep entries current. Add new `Scope` bullets for this change and remove stale scope bullets that no longer reflect repository state.
> **Date integrity rule:** Populate dates/times with runtime commands (for example `date -u`); never guess dates.

## Last updated
- Date: 2026-02-26
- Time (UTC): 04:04:52 UTC
- By: @openai-codex
- Scope: Roadmap lifecycle cleanup: triaged `docs/roadmaps/*`, moved historical artifacts to `docs/archive/roadmaps/`, moved prompt/meta artifacts to `docs/implementation/roadmap-prompts/`, removed stale `web-ui-action-plan.md`, and updated entrypoint docs so only active roadmap artifacts are linked for execution planning.

---

## CI health checklist

| Check | Command | Status | Last run | Notes |
| --- | --- | --- | --- | --- |
| Tests | `pytest -q` | ✅ | 2026-02-26 | Core suites cover parser/rendering, server behavior, contracts, and docs hygiene. |
| Lint | `ruff check .` | ✅ | 2026-02-26 | No lint violations. |
| Format | `ruff format .` | ✅ | 2026-02-26 | Formatting is stable. |
| Docs hygiene | `python scripts/docs_hygiene.py --check-links --check-contradictions --check-status-gates` | ✅ | 2026-02-26 | Validates markdown links, docs-governance workflow references, and entrypoint boundary gates. |
| Package install | `pip install -e ".[dev]"` | ⬜ | — | Validate in clean environment if needed. |
| Docker Compose config | `docker compose config` | ✅ (CI) / ⚠️ (local env) | 2026-02-25 | CI validates compose; local shell in this environment may not include Docker CLI. |

---

## Roadmap status

- **Active operational planning:**
  - `docs/roadmaps/agent-roadmap-v6-multi-repo-orchestration.md`
  - `docs/roadmaps/org-scale-execution-task-cards.md`
- **Archived historical planning:** `docs/archive/roadmaps/README.md`
- **Internal prompt/meta-generation assets:** `docs/implementation/roadmap-prompts/`
- **Removed stale roadmap artifact:** `docs/roadmaps/web-ui-action-plan.md`

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
- Roadmap docs now follow an explicit lifecycle (`active → archived → removed`) with active execution planning isolated in `docs/roadmaps/`.
