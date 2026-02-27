# Storage and deployment

This spec defines **how pm-bot is run** and **where data lives** for the default usage mode:

- **Local-first**
- **Single human operator**
- **Multiple repos** (a “workspace” of repos)
- **Multiple concurrent agents** (via multiple worker processes/containers)
- **No paid cloud services required**

This is deliberately optimized for:

1) You orchestrating agents across repos in your `phys-sims` GitHub org.
2) Others running pm-bot locally for their own repo lists using their own tokens.

## Operating modes

### Mode A (default): local workstation

- You run pm-bot with a single docker-compose stack.
- You open a localhost UI.
- You connect GitHub (PAT or GitHub App) and select repos.
- pm-bot maintains a **local cache** of repo metadata and (optionally) a **local clone** for indexing.
- Agents run via a worker container/process that executes LangGraph graphs.

This mode assumes:
- no multi-user auth
- one operator deciding approvals
- tokens are provided by the user running the instance

### Mode B (optional later): always-on server

Still single-tenant, but runs on a small server you control.
- Polling sync works fine.
- Webhooks are optional and add setup complexity.

**This spec is written for Mode A**. Mode B is a deployment choice, not a redesign.

## Core services (single docker-compose stack)

A practical stack looks like this:

- `api` (control plane backend)
- `ui` (frontend)
- `worker` (execution plane runtime; can be scaled)

Optional services that are still “local and free”:

- `qdrant` (vector DB for RAG) — recommended once you implement RAG
- `postgres` (control-plane DB) — optional escape hatch when SQLite locking becomes a problem

### Minimal stack (v7/v8)

- Control plane DB: SQLite (file)
- Artifacts/checkpoints: filesystem
- GitHub sync: polling

### RAG stack (v10)

Add:
- Qdrant container persisted to local disk (no cloud)

## Persistent data layout

pm-bot should treat persistence as **one directory** mounted into containers.

Recommended layout:

- `data/control_plane/pm_bot.sqlite3`
- `data/control_plane/pm_bot.sqlite3-wal` (WAL file; normal)
- `data/control_plane/pm_bot.sqlite3-shm` (normal)

- `data/artifacts/<run_id>/…`
  - changeset bundles
  - patches
  - logs and tool traces
  - test reports

- `data/checkpoints/<thread_id>/…`
  - LangGraph checkpoints
  - interrupt payload snapshots (if you store them here)

- `data/repos/<owner>/<repo>/…`
  - optional local clones for indexing and tooling (recommended once you do RAG)

- `data/rag/…` (optional)
  - local ingestion state (snapshots)

- `data/qdrant/…` (optional)
  - vector index persisted by the Qdrant container

### Why big blobs must not live in SQLite

SQLite is great for control-plane state but becomes painful when you store large/frequent blobs.

Therefore:
- DB stores **pointers + metadata** (uri, hash, content_type)
- filesystem stores the heavy payloads

This is the #1 reliability win for local deployments.

## Control-plane DB choice

### Default: SQLite

SQLite is the best default for adoption:
- zero setup
- one file
- easy backups

**Required configuration** (non-optional if you run workers concurrently):
- WAL mode
- busy timeout
- short transactions

Operational guidance:
- Keep DB writes small.
- Store tool transcripts and logs as artifacts on disk.

### When to switch to Postgres (still local)

You should switch to Postgres when:
- you run 3+ workers and DB lock contention becomes annoying
- you start doing very high event throughput (lots of audit writes)
- you want stronger concurrency semantics

This still fits your “no cloud cost” goal: Postgres runs as another compose service.

**Design requirement:** migrations/ORM must support SQLite and Postgres.

## GitHub data model: cache + incremental refresh

pm-bot should not “scan GitHub from scratch every time the UI loads.”

Instead:

1) **Repo registry**: user selects which repos are in the workspace.
2) **Initial import**:
   - import open issues/PRs (default) OR a bounded lookback (e.g., last 180 days)
   - optionally shallow-clone repo to `data/repos/...`
3) **Incremental refresh**:
   - polling loop that fetches issues/PRs updated since `last_sync_at`
   - store cursors and timestamps in DB
4) **Manual refresh**:
   - a button in UI triggers a sync job per repo

The cache is used for:
- building ContextPacks
- RAG ingestion
- plan generation / browsing

### Polling defaults

Pragmatic defaults for local mode:
- issues + PRs: poll every 5–10 minutes while stack is running
- repo cloning: update on demand or daily

If you later add webhooks, they should only reduce polling frequency, not replace caching.

## Secrets and token handling

pm-bot should be safe for “others run it locally with their own tokens.”

Rules:
- tokens live in environment variables or local `.env` file
- do not store raw tokens in DB
- redact secrets in logs and audit payloads
- artifacts must not include tokens (run redaction on tool outputs)

Recommended auth paths:
- easiest: GitHub PAT
- best least-privilege: GitHub App (optional later)

## Worker model (multiple agents)

In local mode, “multiple agents” should mean:

- multiple worker processes/containers pulling runnable tasks/runs
- control plane enforces:
  - run approvals
  - tool allowlists
  - budgets
  - concurrency quotas (per repo/tool/provider)

### Scaling workers locally

Use docker compose scaling:
- `docker compose up --scale worker=3`

If you stay on SQLite, keep concurrency modest and keep transactions short.

## Backups and portability

One goal is making pm-bot easy to adopt and move:

- The entire instance state should be captured by:
  - your repo checkout +
  - the `data/` directory

Backup procedure:
1) stop the compose stack
2) copy `data/` somewhere safe

Restore:
1) copy `data/` into place
2) start stack

## UX implications (what the UI should do)

Local-first implies a few UI requirements:

- Setup wizard:
  - enter tokens
  - select repos
  - choose initial import depth
  - start sync and show progress

- Repo dashboard:
  - last sync time
  - indexing status
  - errors

- Controls:
  - “sync now”
  - “reindex now” (v10)
  - “clear cache for repo” (advanced)

## Adoption story for non-org users

The goal is “works out of the box”:

1) clone repo
2) copy `.env.example` → `.env`
3) set `GITHUB_TOKEN` and model provider tokens
4) `docker compose up`
5) open localhost UI and select repos

No accounts, no cloud signup.

## Future-proofing (without overbuilding)

Keep these escape hatches:

- DB can swap SQLite → Postgres
- vector store can swap local Qdrant → something else
- execution runtime is behind RunnerAdapter (LangGraph now, replaceable later)

Do not build multi-tenant SaaS unless you actually need it.
