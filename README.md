# pm-bot

`pm-bot` is an **agent-native project management orchestrator** for turning GitHub issue templates into structured work items, validating them against schema, and coordinating safe write operations through an approval-oriented server surface.

It is designed for deterministic automation: parse issue content into machine-friendly JSON, render canonical issue bodies back from structured data, and provide auditable orchestration primitives for higher-level agents and workflows.

---

## Doc start points

- `STATUS.md` for current repository state, compatibility notes, and health snapshot.
- `docs/README.md` for the authoritative documentation hierarchy and precedence model.
- `docs/spec/pm-agent-native-spec.md` for an integrated navigator overview across contracts/specs/GitHub behavior.

---

## What this repository is for

This repository provides:

- A **CLI** (`pm`) for drafting, parsing, validating, and visualizing work items.
- A **schema-driven parser/renderer** for GitHub issue templates and body sections.
- A **server-layer API** for context packs, guarded changesets, dependency graphing, lightweight estimation snapshots, and weekly reporting.
- A **vendor snapshot** of upstream issue templates and workflow definitions so behavior can remain deterministic during development and testing.

The project is built to support multi-repo planning operations where reliability, compatibility with template headings/labels, and auditability are more important than free-form prose behavior.

---

## Core concepts

### 1) Canonical template inputs
`pm-bot` consumes and normalizes template-driven content sourced from:

- `vendor/dotgithub/ISSUE_TEMPLATE/*.yml`
- `vendor/dotgithub/issue-templates-guide.md`
- `vendor/dotgithub/project-field-sync.yml`

These files are treated as canonical inputs for parser/renderer compatibility.

### 2) Structured work items
Work items are validated against:

- `pm_bot/schema/work_item.schema.json`

This enforces consistent fields such as area, priority, risk, estimates, and dependency references.

### 3) Deterministic parse/render loop
Given an issue body, `pm-bot` can parse sections into structured output; given structured output, it can render canonical markdown sections back. This enables reliable automation and round-tripping.

### 4) Guarded write orchestration
Server APIs model write operations as changesets and apply approval gates and audit trail patterns, reducing risk for automated agents that need to propose repository changes.

---

## Repository layout

- `pm_bot/cli.py` – CLI entrypoint and top-level commands.
- `pm_bot/github/` – template loading, issue body parsing, and issue body rendering logic.
- `pm_bot/schema/` – JSON schemas and template map artifacts.
- `pm_bot/server/` – orchestration app, DB layer, graph, estimator, reporting, and connector modules.
- `tests/` – smoke, parser compatibility, server integration, and v2 behavior tests.
- `vendor/dotgithub/` – vendored template/workflow snapshot used as stable parser input.
- `docs/roadmaps/` – implementation roadmap phases (`v0` through `v3`).
- `reports/` – generated reporting artifacts.

---

## Prerequisites

- Python 3.10+
- `pip`
- Unix-like shell (examples use `bash`)

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Validate installation:

```bash
pm status
```

---

## How to use the CLI

### Draft a new work item body
Generate a draft from template semantics:

```bash
pm draft feature \
  --title "Parser hardening" \
  --context "Ship deterministic handling for label variants" \
  --area platform \
  --priority P1 \
  --validate
```

### Parse an existing issue body file
Convert markdown issue text into structured output:

```bash
pm parse --file issue.md --type feature --validate
```

### Parse from URL

```bash
pm parse --url https://example.com/issue.md --type feature
```

### View dependency tree

```bash
pm tree --file epic.md
```

---

## How to use the server APIs

You can instantiate the local app and call service methods directly:

```bash
python - <<'PY'
from pm_bot.server.app import create_app

app = create_app()

print(
    app.propose_changeset(
        operation="create_issue",
        repo="phys-sims/phys-pipeline",
        payload={"issue_ref": "#1", "title": "Example"},
    )
)
print(app.estimator_snapshot())
print(app.generate_weekly_report())
PY
```

Typical server capabilities include:

- Proposing/approving guarded changesets.
- Building context packs for agent execution.
- Producing graph/tree views of dependencies.
- Generating estimator snapshots (e.g., bucketed percentile estimates).
- Emitting weekly meta-reports.

---

## Keeping vendor templates in sync

The canonical issue templates live upstream; this repository stores a snapshot for deterministic local use.

To refresh the snapshot:

```bash
export PM_BOT_GITHUB_TOKEN=...   # recommended
# or: export GITHUB_TOKEN=...
python scripts/sync_dotgithub.py --ref main
```

After syncing, run tests/lint and confirm parser compatibility remains green.

---

## Compatibility expectations

Project sync relies on headings/labels including:

- `Area`
- `Priority`
- `Size`
- `Estimate (hrs)`
- `Risk`
- `Blocked by`
- `Actual (hrs)`

Note: upstream Epic templates may contain `Size (Epic)`. `pm-bot` maintains compatibility behavior for that variant and normalizes appropriately.

---

## Quality checks

Run these before submitting changes:

```bash
pytest -q
ruff check .
ruff format .
```

---

## Roadmap snapshot

- **v0**: CLI draft/parse/tree with deterministic parse/render + schema support.
- **v1**: Approval-gated write orchestration, webhook ingestion, and context-pack APIs.
- **v2**: Estimator snapshots/predictions, dependency graph/tree APIs, weekly reporting.
- **v3**: SaaS hardening and org-scale controls (planned).

Detailed phase planning lives in `docs/roadmaps/agent-roadmap-v*.md`.

---

## Contributing notes

- Keep changes small, reviewable, and tested.
- Preserve canonical heading labels unless intentionally coordinating compatibility updates.
- Favor deterministic, schema-driven behavior over ad hoc formatting.
- Update `STATUS.md` whenever behavior, tests, schemas, workflows, or roadmap state changes.
