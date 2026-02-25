# pm-bot

`pm-bot` is an **agent-native project management orchestrator** for turning GitHub issue templates into structured work items, validating them against schema, and coordinating safe write operations through an approval-oriented server surface.

It is designed for deterministic automation: parse issue content into machine-friendly JSON, render canonical issue bodies back from structured data, and provide auditable orchestration primitives for higher-level agents and workflows.

---

## Doc start points

- `STATUS.md` for current repository state, compatibility notes, and health snapshot.
- `docs/README.md` for the authoritative documentation hierarchy and precedence model.
- `docs/spec/product.md` for the integrated behavior overview, then drill into focused spec/contract docs as needed.

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
- `docs/roadmaps/` – implementation roadmaps (`v0`-`v2` complete history, near-term `v3`-`v5` execution stages, and separate long-horizon future roadmap).
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

## Quick start (Docker)

Start both API + UI together:

```bash
docker compose up --build
```

Then open:

- UI: `http://localhost:4173`
- API health: `http://localhost:8000/health`

Stop the stack:

```bash
docker compose down
```

Troubleshooting:

- **Port conflict**: if `8000` or `4173` is already in use, stop the conflicting process or adjust host port mappings in `docker-compose.yml`.
- **Clean rebuild**: rebuild all images from scratch with `docker compose build --no-cache`.
- **API base URL override**: default is `http://localhost:8000` so browser requests resolve from the host; change `VITE_PM_BOT_API_BASE` under the `ui` service in `docker-compose.yml` if your backend is reachable at a different URL.

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

## Server startup path (ASGI)

pm-bot now exports an actual ASGI `app` at `pm_bot.server.app:app`. Start it with:

```bash
uvicorn pm_bot.server.app:app --host 127.0.0.1 --port 8000
```

Optional contract check:

```bash
python -m pm_bot.server.app --print-startup
```

Exposed HTTP endpoints for the MVP UI:

- `GET /health`
- `POST /changesets/propose`
- `GET /changesets/pending`
- `POST /changesets/{id}/approve`
- `GET /graph/tree?root=<issue_ref>`
- `GET /graph/deps`
- `GET /estimator/snapshot`
- `GET /reports/weekly/latest`

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


## Web UI (MVP)

A lightweight React + Vite UI now ships under `ui/` with two routes:

- **Inbox**: review and approve pending changesets.
- **Tree**: inspect hierarchy provenance and dependency warnings.

Start backend + UI in separate terminals (native path):

```bash
# terminal 1
uvicorn pm_bot.server.app:app --host 127.0.0.1 --port 8000

# terminal 2
cd ui
npm install
npm run dev -- --host 127.0.0.1 --port 4173
```

Optional tests for UI:

```bash
cd ui
npm test
npm run test:e2e
```

If your API runs on a non-default host/port, set `VITE_PM_BOT_API_BASE`.

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
- **N1 / v3 near-term**: post-v2 hardening, docs/contract alignment, operability.
- **N2 / v4 platform**: single-tenant reliability and policy maturity.
- **N3 / v5 org readiness**: tenant-aware prerequisites and onboarding/compliance prep.
- **Future roadmap**: long-horizon SaaS shape (not default sequencing).

Default execution sequencing:
- `docs/roadmaps/agent-roadmap-v3-near-term.md`
- `docs/roadmaps/agent-roadmap-v4-platform.md`
- `docs/roadmaps/agent-roadmap-v5-org-readiness.md`

Long-horizon/non-executable-now planning:
- `docs/roadmaps/future-roadmap.md`

---

## Contributing notes

- Keep changes small, reviewable, and tested.
- Preserve canonical heading labels unless intentionally coordinating compatibility updates.
- Favor deterministic, schema-driven behavior over ad hoc formatting.
- Update `STATUS.md` whenever behavior, tests, schemas, workflows, or roadmap state changes.
