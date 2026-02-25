# Quickstart

This guide is the shortest path to getting value from pm-bot **safely**.

pm-bot has two “modes”:

- **Local CLI mode** (safe by default): draft/parse/render without writing to GitHub.
- **Server mode** (powerful, but approval-gated): propose → approve → apply changesets, context packs, graph endpoints, reports.

If you haven’t run pm-bot before, do **Local CLI** first, then follow the **First Human Test** runbook before enabling any real GitHub writes.

## Prerequisites

- Python + pip
- (Optional) GitHub token for reading issue bodies by URL (`pm parse --url ...`).
- (Optional) A write-capable GitHub credential (PAT or GitHub App token) **only if** you plan to apply approved changesets.

## Install (editable, dev)

From the repo root:

```bash
pip install -e ".[dev]"
```

This is also the command pm-bot uses in its CI checklist.

## Sanity checks

Run the same checks listed in `STATUS.md`:

```bash
pytest -q
ruff check .
ruff format .
```

If these pass, your environment is sane.

## Local CLI: draft, parse, and tree

> The CLI’s exact flags may evolve. Use `pm --help` to confirm the current interface.

### Draft an issue body from templates

Draft a Feature issue body using canonical headings:

```bash
pm draft feature --title "Add graph view endpoint" --area "cpa-sim" --priority "P1"
```

Expected result:

- A Markdown issue body that preserves the required headings for Projects sync.
- Canonical JSON (WorkItem) that round-trips deterministically.

### Parse an existing issue body file

```bash
pm parse --file path/to/issue.md
```

Expected result: a validated canonical WorkItem JSON output.

### Parse by URL (supported formats)

GitHub issue URL (fetches issue body through the GitHub Issues API):

```bash
pm parse --url https://github.com/<owner>/<repo>/issues/<number>
```

Raw markdown URL (fetches markdown directly):

```bash
pm parse --url https://raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>.md
```

`pm parse --url` supports exactly these URL classes:

- `https://github.com/<owner>/<repo>/issues/<number>`
- `https://.../*.md` (including `raw.githubusercontent.com/.../*.md`)

GitHub issue URLs require auth for private repos (or repos with restricted access). Set `PM_BOT_GITHUB_TOKEN` (preferred) or `GITHUB_TOKEN` with read access.

### Render canonical JSON back to Markdown

The renderer exists as a library (`pm_bot/github/render_issue_body.py`), and is usually exposed either as:

- a CLI command (often `pm render --json ...`), or
- as part of `pm draft` and/or `pm parse` output.

If you don’t see an explicit render command, search for “render” in `pm --help` and consult the repo README.

### Print a tree view

```bash
pm tree --file path/to/epic.md
```

In v0-style workflows, this is typically derived from checklists in Epic/Feature bodies.
In later versions, tree edges SHOULD come from GitHub sub-issues and dependencies (see `docs/github/tree-and-dependencies.md`).

## Server mode (local)

pm-bot includes a server app entrypoint (`pm_bot/server/app.py`) and a local backing store (SQLite).

Use the supported ASGI startup path:

```bash
uvicorn pm_bot.server.app:app --host 127.0.0.1 --port 8000
```

Quick smoke checks:

```bash
python -m pm_bot.server.app --print-startup
curl -s http://127.0.0.1:8000/health
```

Allowlist configuration:

- Default v5 org-ready allowlist includes `phys-sims/.github`, `phys-sims/phys-pipeline`, `phys-sims/cpa-sim`, `phys-sims/fiber-link-sim`, `phys-sims/abcdef-sim`, `phys-sims/fiber-link-testbench`, and `phys-sims/phys-sims-utils`.
- For non-phys-sims usage (or custom subsets), set `PM_BOT_ALLOWED_REPOS`:

```bash
export PM_BOT_ALLOWED_REPOS="my-org/repo-a,my-org/repo-b"
```

Example proposal flow over HTTP:

```bash
curl -s -X POST http://127.0.0.1:8000/changesets/propose \
  -H "content-type: application/json" \
  -d '{"operation":"create_issue","repo":"phys-sims/phys-pipeline","payload":{"issue_ref":"#77","title":"Ingest events"}}'
```

Once running, you typically use the server to:

- ingest issues/webhooks into a local DB
- generate context packs
- create proposed changesets
- approve changesets
- apply approved changesets to GitHub through a connector

Before you do any “apply”, follow:

- `docs/runbooks/first-human-test.md`

## The single most important constraint

If you use GitHub Projects sync, **Projects fields are populated deterministically from issue-body headings**.

That means the issue body MUST preserve the required headings and value placement rules.

Read this before changing templates or rendering code:

- `docs/github/projects-field-sync.md`

## Next steps

- Run the first end-to-end human validation: `docs/runbooks/first-human-test.md`
- Read the product spec to understand intended behavior: `docs/spec/product.md`

