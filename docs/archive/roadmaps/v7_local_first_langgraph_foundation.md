# v7 Roadmap — Local-first foundation + repo restructure for LangGraph

> Archived status: completed and moved from `docs/roadmaps/` to `docs/archive/roadmaps/`.

## Purpose
Make pm-bot usable as a **local-first, single-operator control plane** that can manage many repos without constant re-scanning, and restructure the codebase so LangGraph can be integrated cleanly.

v7 is about getting the *shape* of the system correct:
- control plane vs execution plane separation,
- local persistence layout,
- repo registry + sync cache,
- contracts/docs that make later work deterministic.

This is the milestone that prevents future spaghetti.

## Primary user story
> “I run pm-bot on localhost, connect my GitHub token, select repos in my org, and pm-bot keeps a local cache of issues/PR metadata. I can create plans and runs without waiting on GitHub every time I load a page.”

## Mode A assumptions (explicit)
- Single human operator.
- Local docker-compose stack.
- SQLite is the default relational DB.
- Large/fast-changing blobs (logs, checkpoints, diffs) are stored on filesystem with URIs referenced from DB.
- GitHub access uses a user-supplied token (PAT) in `.env` initially; GitHub App is optional later.
- No multi-tenant auth in v7.

## Exit criteria (definition of done)
1. Repo structure reflects the control plane / execution plane split and builds/tests still run.
2. A persistent local data directory exists (mounted via docker volumes) with stable paths for:
   - SQLite DB
   - artifacts
   - checkpoints
   - local repo mirrors (optional but strongly recommended)
3. A workspace + repo registry exists in DB and is exposed via API:
   - add/list/remove repos
   - show sync status (last sync time, last error)
4. Incremental sync exists for GitHub metadata:
   - initial import (open issues + recent PRs)
   - refresh loop (polling) that only fetches deltas
5. Docs are updated:
   - ADR for architecture split
   - specs for storage/deployment + runtime semantics
   - contracts for AgentRunSpec v2 / RunInterrupt / RunArtifact
   - roadmaps v7+ are present under `docs/roadmaps/`

## Non-goals (explicitly out of scope)
- Running real LangGraph executions (that is v8).
- RAG / vector DB (v10).
- Orchestration DAG scheduling across tasks (v9).
- Full “polished” GUI (v11).
- Multi-user auth/billing.

## Repository restructure plan
### Target package layout (must enforce boundaries)
```
pm_bot/
  control_plane/
    api/
    approvals/
    audit/
    artifacts/
    context/
    db/
    github/
    orchestration/
    models/
  execution_plane/
    langgraph/          # v7: scaffolding only; no runtime yet
  shared/
```

Boundary rules (enforce with tests/lint):
- `control_plane/**` MUST NOT import `langgraph` or `langchain`.
- `execution_plane/**` MUST NOT import control_plane modules directly (use injected interfaces or plain dict contracts).

### Migration approach (how to do it without breaking everything)
1. **Recon**: identify current backend entrypoint(s), routers, DB layer, and any existing “runner” logic.
2. **Create new directories** and move modules:
   - API routers → `control_plane/api`
   - persistence/ORM/models → `control_plane/db` and `control_plane/models`
   - GitHub integration → `control_plane/github`
   - changeset logic/artifacts → `control_plane/artifacts`
   - approvals/inbox → `control_plane/approvals`
   - audit/event log → `control_plane/audit`
   - context pack building → `control_plane/context`
3. Add **compatibility shims** if needed:
   - Keep old import paths temporarily, re-exporting from new modules.
4. Add an import-boundary test (example intent):
   - a test that greps imports or uses Python import hooks to assert `control_plane` does not import `langgraph`.

## Local storage layout (must be standardized now)
Define a single host directory `./data` that is mounted into containers at `/data`.

Required subdirectories:
- `/data/control_plane/pm_bot.sqlite3` (SQLite DB file)
- `/data/artifacts/` (run outputs: changeset bundles, patches, logs)
- `/data/checkpoints/` (LangGraph thread checkpoints later)
- `/data/repos/` (local mirrors/clones; optional but recommended early)
- `/data/cache/` (any derived caches, e.g., rendered diffs, export bundles)
- `/data/logs/` (structured logs if you persist them)

Rules:
- DB stores pointers (URIs) to artifacts/checkpoints, not big blobs.
- Artifact filenames should be content-addressed or include run_id.
- Everything required to reproduce a run should be under `/data` plus GitHub.

## Docker compose requirements (Mode A)
### Services (minimum)
- `api` (control plane server)
- `ui` (frontend)
- `worker` (background workers for sync; execution worker added in v8)

### Volumes
- Mount `./data` → `/data` for api + worker (and optionally ui if it needs artifacts)

### Environment variables (suggested baseline)
- `PMBOT_DATA_DIR=/data`
- `PMBOT_DB_URL=sqlite:////data/control_plane/pm_bot.sqlite3`
- `GITHUB_TOKEN=...` (user-supplied)
- `GITHUB_API_BASE=https://api.github.com` (default)
- `PMBOT_SYNC_POLL_SECONDS=300` (default 5 min)

## Control-plane DB model additions for v7
This is the minimum you need for Mode A caching and governance.

### Workspaces
Even in single-user mode, keep a workspace concept to avoid dead-ends later.
- `workspaces`: workspace_id, name, created_at, settings_json

Create a default workspace automatically on first run.

### Repos
- `repos`: repo_id, workspace_id, full_name, default_branch, status, added_at, last_sync_at, last_error

### Sync cursors (incremental refresh)
- `repo_sync_state`: repo_id, issues_cursor, prs_cursor, last_seen_event_at, last_sync_at, last_error

Cursor strategy:
- Use GitHub `updated_at` timestamps for “fetch deltas since last sync.”
- Store cursors as ISO timestamps; always fetch with overlap window (e.g., 5 minutes) to avoid missing updates.

### Cached GitHub objects (local cache)
Store raw payload JSON and index a few fields:
- `github_issues`: repo_id, issue_number, state, title, updated_at, payload_json
- `github_pull_requests`: repo_id, pr_number, state, title, updated_at, payload_json

Do NOT attempt to normalize everything now. Store raw JSON + minimal indices.

## Sync system design (v7)
### Initial import
User adds a repo; system performs:
- fetch open issues
- fetch open PRs
- optionally fetch last N days of closed items (configurable; default 30–180 days)

### Incremental refresh loop
A background worker:
- iterates repos in workspace
- pulls updates since cursor using `updated_at > cursor - overlap`
- upserts payloads into cache tables
- updates cursor + last_sync_at

### Failure handling
- On API errors, record `last_error` and backoff (exponential).
- UI shows “last sync error” per repo and a manual “sync now” action.

## API endpoints required in v7
(Names may differ based on your framework; keep semantics.)

Workspace:
- `POST /api/workspaces/default` (create/get default)
- `GET /api/workspaces/{id}`

Repos:
- `POST /api/repos` {full_name, default_branch?}
- `GET /api/repos`
- `DELETE /api/repos/{repo_id}`
- `POST /api/repos/{repo_id}/sync` (manual trigger)
- `GET /api/repos/{repo_id}/status` (last_sync_at, last_error, counts)

Cache:
- `GET /api/repos/{repo_id}/issues?state=open&limit=...`
- `GET /api/repos/{repo_id}/prs?state=open&limit=...`

## Minimal UI needs in v7 (do not wait for v11)
You do not need a polished UI, but you do need:
- a “Repos” page to add/list repos and see sync status
- a “Sync now” button
- a simple setup status banner (“GitHub token present?”)

If your UI is currently plan/run-focused, add this as a small new page, not a redesign.

## Tests & runbooks (required evidence)
### Tests
- import-boundary test (control_plane can’t import langgraph)
- DB initialization test (tables created, default workspace created)
- sync worker unit tests with mocked GitHub responses
- sync cursor correctness test (no missing updates when overlap window used)

### Runbooks
Add `docs/runbooks/first-local-setup.md`:
- copy `.env.example`
- start docker compose
- add repo
- verify cache tables populated
- verify incremental refresh updates items

## Rollout/rollback strategy
- All changes should be additive and behind feature flags where possible.
- If sync worker fails, UI should still function using stale cache (read-only).
- A “Reset local cache” action should exist (dangerous but necessary) that wipes cached GitHub tables without deleting run history.

## Known pitfalls (tell-it-like-it-is)
- If you put large artifacts/checkpoints in SQLite, you will get lock pain quickly.
- If you rescan GitHub on every UI page load, you will hit rate limits and UX will be awful.
- If you don’t enforce import boundaries early, you will end up with LangGraph coupled everywhere.

