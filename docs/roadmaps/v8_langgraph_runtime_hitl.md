# v8 Roadmap — LangGraph runtime + HITL interrupts + first real run

## Purpose
Make agent execution **real** using LangGraph while preserving pm-bot’s governance invariants:
- approvals before token spend,
- interrupts for human decisions mid-run,
- artifacts produced for review (not auto-applied),
- audit trail for everything.

v8 turns pm-bot from “a control plane + cache” into “a control plane that can run agents safely.”

## Primary user story
> “I approve a run, it executes via LangGraph, it pauses for decisions (interrupts), and it produces a proposed ChangesetBundle artifact that I can review and apply.”

## Assumptions (Mode A)
- Single operator on localhost.
- Local docker-compose with separate `worker` for execution.
- SQLite DB + filesystem artifact/checkpoint storage.
- GitHub token provided by operator.
- LLM provider keys provided by operator.

## Exit criteria (definition of done)
1. A LangGraphRunnerAdapter exists with working semantics:
   - submit → thread_id created and persisted
   - poll → returns running/blocked/completed/failed
   - resume → continues from interrupt decision
   - cancel → stops execution safely
   - fetch_artifacts → lists artifacts produced by run
2. Interrupts are first-class objects:
   - created by execution plane
   - stored in DB
   - surfaced in Inbox UI
   - resolvable (approve/edit/reject) and resume works
3. At least one canonical graph exists and runs end-to-end:
   - `repo_change_proposer/v1`
   - produces a ChangesetBundle artifact (JSON) stored in artifact store
4. Budgets and tool allowlists are enforced in runtime:
   - token limit, tool call limit, wall clock limit
5. Audit events exist for:
   - run start/stop
   - each model call (provider/model/tokens)
   - each tool call (name/args redacted/duration/result summary)
   - each interrupt raised/resolved
6. No GitHub writes happen during execution (only proposals).

## Non-goals
- Full orchestration DAG across tasks (v9).
- RAG/vector DB (v10).
- Fancy GUI (v11).
- Multi-user auth.

## Contracts and data model updates required
### AgentRunSpec v2 usage (execution config)
Run spec must include:
- engine = "langgraph"
- graph_id (semantic versioned)
- thread_id (null at creation; set after submit)
- budgets: max_total_tokens / max_tool_calls / max_wall_seconds
- tools_allowed list
- scopes.repo (owner/repo)

### RunInterrupt v1
Interrupt object persisted by control plane:
- interrupt_id, run_id, thread_id
- kind: approve_tool_call | approve_spend | approve_publish | question
- risk: low/medium/high
- payload (redacted)
- decision metadata

### RunArtifact v1
Artifacts persisted with URI:
- changeset_bundle, patch, log, tool_trace, test_report, etc.

### Checkpoint storage (pragmatic default)
- Store checkpoint blobs under `/data/checkpoints/{thread_id}/...`
- Store minimal metadata in DB:
  - last_checkpoint_path
  - last_checkpoint_at
  - last_known_status
Rationale: avoids heavy DB writes/locks with SQLite.

## Execution plane architecture (LangGraph)
### RunnerAdapter boundary (must be strict)
Control plane must call a single adapter:
- submit(run_spec) -> thread_id
- poll(run_spec) -> status + optional interrupt
- resume(run_spec, decision)
- cancel(run_spec)
- fetch_artifacts(run_spec)

Adapter responsibilities:
- validate run approval exists before starting execution
- create/persist thread_id
- enforce budgets and tool allowlists
- capture and persist interrupts + audit events
- write artifacts via artifact store interface

### Graph registry and graph IDs
Implement a graph registry mapping `graph_id` strings to constructors:
- `repo_change_proposer/v1` → build graph object

Graph IDs MUST be versioned and stable; do not use Python function names as IDs.

## Canonical graph: repo_change_proposer/v1
### Purpose
Given:
- a goal,
- a repo scope,
- a ContextPack (built by control plane),
propose a ChangesetBundle artifact.

### Inputs (state)
- run_id, thread_id
- goal text
- repo_full_name
- context_pack_id or serialized content
- budgets + tools_allowed

### Outputs
- artifact: ChangesetBundle proposal (JSON)
- audit: model call metadata
- optional logs/tool traces

### Minimal nodes (v1)
1. `load_context_pack`
   - load serialized context from control plane or artifact store
2. `plan`
   - LLM produces a short plan (optional, but helps)
3. `propose_changeset_bundle`
   - LLM produces strict JSON matching ChangesetBundle contract
4. `emit_artifact`
   - store ChangesetBundle in artifact store and create RunArtifact entry

### Interrupt boundaries (must be explicit)
- Before any external tool call (including repo_checkout, test runner).
- Before exceeding budget thresholds (optional: interrupt when >80% tokens used).
- Before any “publish” action (PR draft creation) if you add it later.

### Idempotency rules (LangGraph reality)
Because resume can rerun a node:
- nodes must not cause irreversible side effects before interrupts
- tools must be idempotent (check existence before create)

## Tooling: minimal tool registry (safe, local-first)
Start with read-only / local operations:
- `github_read` (issues/PRs via API; rate-limited)
- `repo_checkout` (clone/fetch repo to `/data/repos/...`)
- `repo_read_file` (read from local clone)
- `repo_search` (ripgrep over local clone)
- `run_tests` (optional; local test command; should be interrupt-gated)

Important: “write” tools do not write to GitHub. They can only:
- generate patches as artifacts
- generate ChangesetBundles

## Worker model (Mode A)
Add an `execution-worker` service in docker-compose:
- polls DB for approved runs in “queued” state
- claims a run (lease) to avoid double execution
- calls adapter.submit/poll loop until completion or interrupt
- on interrupt, stops and updates status to blocked

Rationale:
- keeps API responsive
- allows running multiple agents concurrently on one machine

Lease model:
- run table fields: leased_by, lease_expires_at
- worker renews lease periodically
- if worker crashes, lease expires and run can be reclaimed

## API surface required in v8
Runs:
- `POST /api/runs` create run (proposed)
- `POST /api/runs/{run_id}/approve` approve run start
- `GET /api/runs/{run_id}` includes status, thread_id, budgets used
- `POST /api/runs/{run_id}/cancel`
- `GET /api/runs/{run_id}/artifacts`

Interrupts / Inbox:
- `GET /api/inbox` includes interrupt items
- `GET /api/interrupts/{interrupt_id}`
- `POST /api/interrupts/{interrupt_id}/resolve` (approve/reject/edit)
  - record decision, then resume run

Audit:
- `GET /api/runs/{run_id}/audit` returns timeline events

## Minimal UI changes required in v8 (do not wait for v11)
- Inbox shows interrupt items and run approvals
- Interrupt detail view with approve/edit/reject actions
- Run detail view:
  - status, budgets used, artifacts list, audit timeline (can be simple list)

## Testing & evidence (must be real)
### Unit tests
- adapter refuses to start unapproved run
- tool allowlist enforced (disallowed tool triggers interrupt/fail)
- budget enforcement (token/tool/wall)

### Integration tests (mocked LLM)
- repo_change_proposer graph produces a ChangesetBundle artifact
- interrupt resolution resumes execution and completes

### Runbook
Add `docs/runbooks/first-langgraph-run.md`:
- start stack
- add repo
- create run for simple goal
- approve
- resolve interrupt if any
- review artifact

## Rollout/rollback
Feature flags (config):
- `PMBOT_ENABLE_LANGGRAPH_EXECUTION`
- `PMBOT_ENABLE_EXECUTION_WORKER`
- `PMBOT_ENABLE_TEST_TOOL` (if you add run_tests)

Rollback:
- disable flags → runs remain manual or queued, no execution
- audit is append-only; never delete failed run attempts

## Known pitfalls
- If you let nodes/tools write to GitHub directly, pm-bot loses its core safety property.
- If you don’t store thread_id and checkpoint paths durably, resume will be flaky.
- If you don’t enforce budgets, you will burn tokens silently.
- If you don’t design idempotent nodes, resume will duplicate side effects.

