# pm-bot
> **Audience:** Contributors and operators evaluating the repository.
> **Depth:** L0 (orientation).
> **Source of truth:** Entry-point orientation only; not normative for behavior or contracts.


`pm-bot` is an agent-native project management orchestrator for deterministic, schema-driven GitHub issue and project workflows.

## Orientation

This repository uses a strict 3-level docs entrypoint model:

1. **`README.md` (this file):** quick orientation plus install/run commands.
2. **`docs/README.md`:** canonical documentation IA, precedence rules, and section ownership.
3. **`STATUS.md`:** current operational health, compatibility notes, and active change scope bullets.

Primary links:

- Documentation IA and precedence: [`docs/README.md`](docs/README.md)
- Product behavior spec: [`docs/spec/product.md`](docs/spec/product.md)
- Operational status snapshot: [`STATUS.md`](STATUS.md)

## Roadmap (active planning only)

- Active roadmap index: [`docs/roadmaps/README.md`](docs/roadmaps/README.md)
- Foundational multi-repo stage: [`docs/roadmaps/agent-roadmap-v6-multi-repo-orchestration.md`](docs/roadmaps/agent-roadmap-v6-multi-repo-orchestration.md)
- Current stage set: `docs/roadmaps/v8_langgraph_runtime_hitl.md` → `docs/roadmaps/v11_gui_rebuild.md`
- Archived execution task cards: [`docs/archive/roadmaps/org-scale-execution-task-cards.md`](docs/archive/roadmaps/org-scale-execution-task-cards.md)

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

CLI health check:

```bash
pm status
```

Start API server:

```bash
uvicorn pm_bot.server.app:app --host 127.0.0.1 --port 8000
```

Optional local stack (API + UI):

```bash
docker compose up --build
```
