# pm-bot

`pm-bot` is an agent-native project management orchestrator for deterministic, schema-driven GitHub issue and project workflows.

## Orientation

This repository uses a strict 3-level docs entrypoint model:

1. **`README.md` (this file):** quick orientation plus install/run commands.
2. **`docs/README.md`:** canonical documentation IA, precedence rules, and section ownership.
3. **`STATUS.md`:** current operational health, validation checks, and recent scope deltas.

Primary links:

- Documentation IA and precedence: [`docs/README.md`](docs/README.md)
- Product behavior spec: [`docs/spec/product.md`](docs/spec/product.md)
- Operational status snapshot: [`STATUS.md`](STATUS.md)

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
