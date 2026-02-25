# Repo inventory (pm-bot)

_Date generated (UTC): 2026-02-25T03:48:20Z (runtime commands captured below)_

This inventory is the mandatory baseline for mapping org-scale roadmap work onto the current repository.

## 1) Root layout snapshot

Command:

```bash
ls -la
```

Observed top-level areas:

- Backend/service: `pm_bot/`
- Frontend: `ui/`
- Contracts/spec/docs: `docs/`
- Tests: `tests/`
- Canonical template inputs: `vendor/`

## 2) Backend entrypoint and ASGI command

Command:

```bash
rg -n "uvicorn|fastapi|starlette|asgi" .
```

Findings:

- Server startup command is documented and emitted as:
  - `uvicorn pm_bot.server.app:app --host 127.0.0.1 --port 8000`
- Primary app module: `pm_bot/server/app.py`

## 3) Storage layer and migrations

Command:

```bash
rg -n "sqlite|sqlalchemy|alembic|migrate|migrations" .
```

Findings:

- SQLite is the active persistence layer (`sqlite3`) in `pm_bot/server/db.py`.
- No Alembic/SQLAlchemy migration framework detected in current tree.
- Schema lifecycle is managed in application DB setup code.

## 4) Existing contracts and model terms

Command:

```bash
rg -n "WorkGraph|changeset|AgentRunSpec|context pack|context_pack" .
```

Findings:

- Contract docs exist for the major control-plane objects in `docs/contracts/`:
  - `workgraph.md`
  - `changesets.md`
  - `context_pack.md`
  - `agent_run_spec.md`
- Server modules already implement workgraph/context pack/changeset behavior in:
  - `pm_bot/server/graph.py`
  - `pm_bot/server/context_pack.py`
  - `pm_bot/server/changesets.py`

## 5) Approval flow inventory

Command:

```bash
rg -n "approve|approval|changeset" pm_bot/server tests
```

Findings:

- Approval-gated changeset flow exists in server code and HTTP routes.
- Pending approvals endpoint exists (`/changesets/pending`).
- Approval denial reason-code tests already exist (`tests/test_server_http_contract.py`).

## 6) GitHub integration wrapper

Command:

```bash
rg -n "api.github.com|octokit|PyGithub|requests.*github|gh_" .
```

Findings:

- GitHub REST usage is centralized through connector modules under `pm_bot/server/` and CLI path usage in `pm_bot/cli.py`.
- Default base API URL is `https://api.github.com` in `pm_bot/server/github_connector_api.py`.
- Local tooling for canonical input sync exists in `scripts/sync_dotgithub.py`.

## 7) UI pages and routes implemented

Command:

```bash
rg -n "inbox|tree|graph|changeset|approval" ui/
```

Findings:

- Implemented React pages/components:
  - `InboxPage` (pending changesets + approve action)
  - `TreePage` (tree + dependency warnings)
- App route toggle currently supports `inbox` and `tree` views in `ui/src/App.tsx`.
- UI API bindings already target:
  - `/changesets/pending`
  - `/changesets/{id}/approve`
  - `/graph/tree`
  - `/graph/deps`

## 8) Mapping implications for org-scale roadmap

- Current baseline is not “greenfield”: it already includes approval-gated writes, context packs, graph API, and inbox/tree UI primitives.
- Recommended next roadmap decomposition should **extend** v5 org-readiness and add explicit phases for:
  1. cross-repo graph ingestion and typed edge provenance hardening,
  2. context pack v2 determinism/audit upgrades,
  3. runner control-plane adapters + queue semantics,
  4. unified inbox aggregation with GitHub search constraints.
