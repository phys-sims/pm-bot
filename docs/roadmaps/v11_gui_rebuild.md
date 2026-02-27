# v11 Roadmap — GUI rebuild for local-first orchestration, interrupts, and artifacts

## Purpose
pm-bot’s value is human control. If the GUI cannot supervise:
- repo sync/index state,
- run approvals and interrupts,
- orchestration DAG progress,
- artifact review (changeset diffs),
then pm-bot is not usable beyond a demo.

v11 rebuilds/extends the UI to make pm-bot a practical local-first tool.

## Mode A assumptions
- Single operator, localhost UI.
- No complex auth; no multi-tenant.
- Everything is local: DB + filesystem + local services (Qdrant optional).
- UI must handle “offline-ish” situations gracefully (GitHub token missing, sync paused).

## Exit criteria (definition of done)
1. First-run onboarding is smooth:
   - detects missing tokens and explains how to set them
   - repo selection and initial sync is discoverable
2. Repo dashboard exists:
   - per repo: sync status, last sync time, last error
   - per repo: index status (if v10 enabled): last indexed commit, chunk count, last error
   - manual actions: sync now, index now, reindex
3. Unified Inbox exists:
   - run approvals (start token spend)
   - interrupts (tool approval / budget / publish / questions)
   - changeset approvals (apply)
   - orchestration approvals (if you add envelope approvals)
4. Run detail view is operator-grade:
   - status, budgets used
   - timeline (audit events)
   - artifacts list (changeset bundle, logs, traces)
   - interrupt history
5. Orchestration view exists (readable):
   - DAG graph or list with dependencies
   - task/run statuses
   - click-through to task run details
6. Artifact viewers exist:
   - ChangesetBundle diff viewer is first-class
   - log/tool trace viewer is usable
7. Operator actions exist and are safe:
   - cancel run
   - retry run/task (never bypass approvals)
   - export “incident bundle” (audit + logs + artifacts)

## Non-goals
- Pixel-perfect design.
- Multi-user auth or permissions.
- SaaS admin panels.

## UI information architecture (recommended)
Top-level navigation:
- **Setup** (first-run only; hidden after configured)
- **Repos** (sync + index status)
- **Inbox** (approvals + interrupts + changesets)
- **Runs** (single-run list)
- **Orchestrations** (DAG view; v9+)
- **Artifacts** (optional global search)

## First-run onboarding (must exist in v11)
### Setup wizard requirements
- Detect whether required env vars are set:
  - GitHub token present?
  - LLM provider key present?
  - Data directory mounted?
- If missing, show copy-paste instructions:
  - where to put `.env`
  - how to restart compose
- Repo selection UX:
  - list repos discovered from GitHub org/user (if token present)
  - allow manual entry `owner/repo`
- Initial sync action:
  - show progress (counts, last error)
  - allow “import depth” choice (open only vs last N days)

## Repo dashboard (v11)
For each repo show:
- repo name/link
- last_sync_at
- last_sync_error (collapsed but visible)
- counts: open issues, open PRs (from cache)
- last_indexed_commit (if v10 enabled)
- index job status (running/completed/failed)
Actions:
- sync now
- index now
- reindex latest
- clear local cache (danger: confirm)

## Unified Inbox (v11)
Inbox item types:
- run approval: “start run”
- interrupt: approve/edit/reject
- changeset approval: review/apply
- orchestration-level items (optional)

Inbox requirements:
- sort by risk + time:
  - high-risk interrupts first
- each item includes:
  - summary
  - repo
  - estimated cost/risk (if available)
  - primary action buttons

## Run detail view (v11)
Sections:
1. Header:
   - run_id, repo, graph_id, thread_id
   - status + timestamps
2. Budgets:
   - token used / max
   - tool calls used / max
   - wall time used / max
3. Timeline:
   - audit events grouped by node/tool/model call
4. Interrupts:
   - list of interrupts + decisions
5. Artifacts:
   - list with viewers:
     - ChangesetBundle viewer
     - logs viewer
     - tool trace viewer
6. Actions:
   - cancel
   - retry (creates a new run requiring approval)
   - export bundle

## Orchestration view (v11)
Minimum viable:
- DAG as list grouped by “ready/running/blocked/completed”
Better:
- Graph visualization with edges (but keep readable)

Must show:
- critical path and blockers
- which task is blocked on interrupt
- ability to jump from task to run detail

## Artifact viewers
### ChangesetBundle viewer (non-negotiable)
- show file list
- show diffs (side-by-side or unified)
- show metadata: why change, which task produced it, tests run

### Log viewer / tool trace viewer
- structured display of tool calls:
  - tool name
  - args (redacted)
  - duration
  - result summary
- show raw payload behind “expand” control

## API additions likely needed for v11
Even if backend already has some endpoints, UI needs stable APIs:

Setup/status:
- `GET /api/status` (env var presence flags, version, data dir)
- `GET /api/workspaces/default`

Repos:
- existing v7 endpoints +:
  - `GET /api/repos/{repo_id}/index-status`
  - `POST /api/repos/{repo_id}/index` (trigger)

Inbox:
- `GET /api/inbox`
- `POST /api/inbox/{item_id}/resolve` (dispatches to proper resolver)

Runs:
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/audit`
- `GET /api/runs/{run_id}/artifacts`

Orchestrations:
- v9 endpoints for DAG

Artifacts:
- `GET /api/artifacts/{artifact_id}` or file-serving endpoint

## Local-first UX constraints (important)
- UI must be resilient to stale cache:
  - show “last synced at”
  - allow manual sync
- UI must not freeze waiting for GitHub:
  - always use local cache for listing
  - background sync updates asynchronously

## Testing & evidence
- end-to-end smoke test runbook:
  - setup → add repo → sync → create run → approve → resolve interrupt → review changeset → apply
- UI component tests:
  - Inbox resolution flows
  - Changeset diff viewer renders correctly on sample artifacts

## Rollout/rollback
- UI routes can be feature-flagged.
- Backend remains source of truth; UI can be reverted without data loss.

## Pitfalls
- If onboarding is bad, nobody adopts pm-bot.
- If Inbox is fragmented, runs will stall.
- If diff review is painful, humans will not trust or use it.

