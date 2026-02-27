# Local-first storage runbook
> **Audience:** Operators and contributors running pm-bot locally.
> **Depth:** L1 (runbook).
> **Source of truth:** Local-first persistent storage layout and operational defaults.

This runbook describes the default on-disk layout for pm-bot.

## Data directory

By default, pm-bot stores durable state under `./data`:

- `data/control_plane/pm_bot.sqlite`
- `data/artifacts/`
- `data/checkpoints/`
- `data/repos/`

Environment variables:

- `PMBOT_DATA_DIR` (default `./data`)
- `PMBOT_SQLITE_PATH` (default `./data/control_plane/pm_bot.sqlite`)
- `PMBOT_ARTIFACT_DIR` (default `./data/artifacts`)
- `PMBOT_CHECKPOINT_DIR` (default `./data/checkpoints`)
- `PMBOT_REPOS_DIR` (default `./data/repos`)

## SQLite runtime settings

At connection time the control-plane DB sets:

- `PRAGMA journal_mode=WAL`
- `PRAGMA busy_timeout=5000`
- `PRAGMA synchronous=NORMAL`
- `PRAGMA foreign_keys=ON`
- `PRAGMA temp_store=MEMORY`

These settings improve durability and concurrent-reader behavior in local multi-process workflows.

## Docker compose persistence

`docker-compose.yml` mounts `./data` into the backend container at `/data` and configures PMBOT storage environment variables to `/data/...` paths.

As long as `./data` remains on disk, DB state survives container restarts.

## Artifact policy

Artifacts/checkpoints are filesystem-first. The database should store paths/URIs and metadata only, not large blobs.
