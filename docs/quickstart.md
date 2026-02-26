# Quickstart
> **Audience:** First-time operators and contributors.
> **Depth:** L1 (procedural usage).
> **Source of truth:** Practical onboarding path. For normative behavior, defer to L2 specs and L3 contracts.

This guide is the shortest safe path to first value with pm-bot.

## 1) Install

From repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## 2) Validate local environment

Run the baseline checks listed in `STATUS.md`:

```bash
pytest -q
ruff check .
ruff format .
python scripts/docs_hygiene.py --check-links --check-contradictions --check-status-gates --check-depth-metadata --check-l0-bloat
```

## 3) Run pm-bot in local-safe mode

Use local CLI flows first so nothing writes to GitHub:

```bash
pm draft feature --title "Add graph view endpoint" --area "cpa-sim" --priority "P1"
pm parse --help
pm tree --help
```

If CLI flags drift, use:

```bash
pm --help
```

## 4) Validate GitHub compatibility before any writes

Before write-capable operation, complete the first human validation runbook:

- [`docs/runbooks/first-human-test.md`](runbooks/first-human-test.md)

This is mandatory because Projects sync depends on strict issue-body heading formatting.

## 5) Learn deeper contracts only when needed

Use depth-first links instead of this guide as source-of-truth:

- L2 behavior specs: [`docs/spec/product.md`](spec/product.md), [`docs/spec/graph-api.md`](spec/graph-api.md), [`docs/spec/reporting.md`](spec/reporting.md)
- L2 GitHub integration detail: [`docs/github/projects-field-sync.md`](github/projects-field-sync.md), [`docs/github/auth-and-tokens.md`](github/auth-and-tokens.md), [`docs/github/tree-and-dependencies.md`](github/tree-and-dependencies.md)
- L3 normative contracts: [`docs/contracts/README.md`](contracts/README.md), [`pm_bot/schema/work_item.schema.json`](../pm_bot/schema/work_item.schema.json)

## 6) Optional: server mode

Start API server only after passing local checks and runbook validation:

```bash
uvicorn pm_bot.server.app:app --host 127.0.0.1 --port 8000
```

Server and approval semantics are defined in L2/L3 docs; this page intentionally links out rather than duplicating those rules.
