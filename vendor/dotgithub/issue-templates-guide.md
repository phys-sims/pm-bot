# Templates Guide for phys-pipeline

This guide covers the issue templates, the pull request template, and the ADR templates.

## Epic
Use for multi-issue efforts delivering a demo-level outcome.
Required fields: Objective, Scope, Success Metrics, Area.
Includes milestones and child issue links.

## Feature
Use for new capabilities or significant refactors.
Required fields: Goal, Priority, Area.
Include acceptance criteria and child tasks.

## Task
Use for small work items (<= 2 days).
Reference the parent feature URL.
Include acceptance criteria and size/estimate.

## Bug
Use when something broke or behavior regressed.
Include repro steps, expected vs actual, and logs.

## Benchmark
Use for performance measurement.
Include scenario (graph size, cache mode, eval count) and metrics to capture.

## Spike
Use for time-boxed investigation and risk reduction.
Include question, plan, and exit criteria.

## Test
Use for validation work: physics or engineering.
Specify test type and reference or contract.

## Chore / Infra
Use for CI, lint, docs, build, and repo hygiene changes.
Describe current pain, change, and acceptance criteria.

## Pull Request Template
Fill all sections in `.github/pull_request_template.md`.

What
Summarize the change in 1 to 3 bullets.

Why
Link the issue or decision the PR addresses.

How
List the key changes by file or behavior.

Tests
Check the boxes that apply. For docs-only PRs, note not applicable.

Artifacts
Attach notebooks, plots, or CSVs when relevant to the change.

Checklist
Confirm docs and compatibility.

## ADR Templates
ADR templates live in `docs/adr/`:
- `_template-full.md` for significant architectural decisions.
- `_template-lite.md` for small or narrow decisions.
- `_template-amend.md` for updates to existing ADRs.

Create ADRs with `python scripts/adr_tools.py new "Title" --type full`.
Update the index with `python scripts/adr_tools.py reindex`.

## Tips for PMs
- Use Epic for multi-team or multi-sprint outcomes.
- Track progress by linking child issues inside Epics and Features.
- Use Spike when uncertainty is high and the output is a decision or report.
- Use Test issues to make validation explicit and traceable.

## Codex issue automation
Use the GitHub Actions workflow `Codex Issue Generator` to draft issues from the templates.

Workflow inputs:
- `issue_type`: Select the template (`epic`, `feature`, `task`, `bug`, `benchmark`, `spike`, `test`, `chore`).
- `title`: Provide the issue title, including any prefix from the template.
- `context`: Supply the background, links, and constraints for Codex to follow.
- Optional: `labels`, `assignees`, and `model`.

Operational notes:
- Configure the `OPENAI_API_KEY` repository secret so Codex can generate the body.
- The workflow reads this guide and the chosen template to enforce required fields.
- Keep the context aligned with PM tips to ensure consistent scope and acceptance criteria.
