# Project Status (pm-bot)

> **Source of truth:** Update this file whenever behavior, tests, schemas, workflows, or canonical inputs change.
> **Agent rule:** Keep entries current and prune stale content in the same change.
> **Date integrity rule:** Populate dates/times with runtime commands (for example `date -u`); never guess dates.

## Last updated
- Date: 2026-02-26
- Time (UTC): 04:26:27 UTC
- By: @openai-codex

---

## CI health checklist

| Check | Command | Status | Last run | Notes |
| --- | --- | --- | --- | --- |
| Tests | `pytest -q` | ✅ | 2026-02-26 | Core suites cover parser/rendering, server behavior, contracts, and docs hygiene. |
| Lint | `ruff check .` | ✅ | 2026-02-26 | No lint violations. |
| Format | `ruff format .` | ✅ | 2026-02-26 | Formatting is stable. |
| Docs hygiene | `python scripts/docs_hygiene.py --check-links --check-contradictions --check-status-gates --check-depth-metadata --check-l0-bloat` | ✅ | 2026-02-26 | Validates markdown links, docs-governance workflow references, status-shape gates, and L0/depth metadata limits. |
| Package install | `pip install -e ".[dev]"` | ⬜ | — | Validate in clean environment if needed. |
| Docker Compose config | `docker compose config` | ✅ (CI) / ⚠️ (local env) | 2026-02-25 | CI validates compose; local shell in this environment may not include Docker CLI. |

---

## Current compatibility notes

- Canonical inputs:
  - `vendor/dotgithub/ISSUE_TEMPLATE/*.yml`
  - `vendor/dotgithub/issue-templates-guide.md`
  - `vendor/dotgithub/project-field-sync.yml`
  - `pm_bot/schema/work_item.schema.json`
- Required tracked headings/labels for project sync:
  `Area`, `Priority`, `Size`, `Estimate (hrs)`, `Risk`, `Blocked by`, `Actual (hrs)`.
- Known compatibility shim:
  Epic template currently uses `Size (Epic)`; parser compatibility shim is implemented and renderer normalizes to `Size`.

---

## Active change scope bullets

> **Template + stale content pruning instructions:**
> - Keep only bullets for currently active/recently landed changes that still describe repository reality.
> - Remove superseded bullets in the same PR that introduces replacement behavior/docs/tests.
> - Do not keep historical roadmap narratives/checklists here; place durable planning content in `docs/roadmaps/` (active) or `docs/archive/roadmaps/` (historical).

- Redesigned `STATUS.md` to the four approved sections and removed embedded roadmap/state narrative blocks.
- Updated docs entrypoint wording so `README.md` and `docs/README.md` no longer imply roadmap detail is tracked in `STATUS.md`.
- Tightened docs hygiene status gates to detect legacy/superseded status blocks and stale scope-bullet patterns.
