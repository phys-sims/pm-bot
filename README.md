# phys-sims/pm-bot (scaffold)

Agent-native PM orchestrator for multi-repo work.

This repo is intentionally scaffolded so **Codex (cloud / action / CLI)** can implement it by following:
- `docs/roadmaps/agent-roadmap-v0.md`
- `docs/roadmaps/agent-roadmap-v1.md`
- `docs/roadmaps/agent-roadmap-v2.md`
- `docs/roadmaps/agent-roadmap-v3.md`

## Why vendor templates?
The canonical issue templates + field sync live in `phys-sims/.github`.

For Codex tasks, we keep a snapshot copy in:
- `vendor/dotgithub/ISSUE_TEMPLATE/*.yml`
- `vendor/dotgithub/project-field-sync.yml`
- `vendor/dotgithub/issue-templates-guide.md`

Update the snapshot with:
```bash
export PM_BOT_GITHUB_TOKEN=...   # recommended
# or: export GITHUB_TOKEN=...
python scripts/sync_dotgithub.py --ref main
```

## Quickstart
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e "[dev]"
pm status
```

## Roadmap status
- v0: CLI draft/parse/tree plus deterministic parse/render and WorkItem schema are implemented in `pm_bot/`.
- v1: approval-gated write orchestrator, webhook ingestion, and context-pack APIs live under `pm_bot/server/`.
- v2: estimator snapshots + predictions, graph/tree APIs, and weekly meta-report generation are implemented in `pm_bot/server/`.

## Key commands
```bash
# v0
pm draft feature --title "Parser" --context "Ship parser" --area platform --priority P1 --validate
pm parse --file issue.md --type feature --validate
pm parse --url https://example.com/issue.md --type feature
pm tree --file epic.md

# v1/v2 (library usage)
python - <<'PY'
from pm_bot.server.app import create_app
app = create_app()
print(app.propose_changeset(operation="create_issue", repo="phys-sims/phys-pipeline", payload={"issue_ref": "#1", "title": "Example"}))
print(app.estimator_snapshot())
print(app.generate_weekly_report())
PY
```
