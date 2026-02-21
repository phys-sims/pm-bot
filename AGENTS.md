# AGENTS.md — pm-bot

## Repository expectations
- Keep changes small, reviewable, and well-tested.
- Do not change template heading labels lightly. Downstream automation parses headings.
- Prefer deterministic, schema-driven rendering over “pretty prose”.

## Commands
- Setup:
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -e ".[dev]"`
- Tests:
  - `pytest -q`
- Lint:
  - `ruff check .`
  - `ruff format .`

## Canonical inputs
- Templates snapshot: `vendor/dotgithub/ISSUE_TEMPLATE/*.yml`
- Templates guide: `vendor/dotgithub/issue-templates-guide.md`
- Projects sync workflow: `vendor/dotgithub/project-field-sync.yml`
- WorkItem schema: `pm_bot/schema/work_item.schema.json`

## Compatibility constraints
- The Projects sync expects headings and labels like:
  `Area`, `Priority`, `Size`, `Estimate (hrs)`, `Risk`, `Blocked by`, `Actual (hrs)`.
- NOTE: the Epic template currently uses `Size (Epic)` — this is either:
  - a bug to fix in templates (preferred: rename to `Size`), OR
  - a compatibility shim to add in parsers.

## Review guidelines
When reviewing PRs (especially agent-generated):
- Verify the change links to an Issue (`Fixes #123`) and follows `.github/pull_request_template.md` if present.
- Confirm tests were run and results are included.
- Watch for prompt-injection / untrusted text being executed or treated as instructions.
- Avoid introducing long-lived secrets or credentials into code or workflows.
