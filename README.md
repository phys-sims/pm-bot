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
export GITHUB_TOKEN=...
python scripts/sync_dotgithub.py --ref main
```

## Quickstart
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pm status
```

## Next steps
- Implement v0 commands (draft/parse/render/tree) in `pm_bot/` per roadmap.
- Add `AGENTS.md` rules for Codex.
