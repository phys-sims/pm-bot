# v9 Roadmap — Orchestration DAG + bounded concurrency (many tasks, one operator)

## Purpose
Enable the headline capability:
> “High-level plan/report → concurrent agents implement subtasks → human gates + GUI.”

v8 gives you safe single-run execution. v9 scales that into **many tasks** with:
- explicit dependencies (DAG),
- bounded concurrency and quotas,
- multi-worker execution,
- aggregated outputs for human review.

This is the point where pm-bot becomes an orchestrator, not just a runner.

## Mode A assumptions
- Single operator on localhost.
- One docker-compose stack.
- SQLite + filesystem persistence by default.
- Optional multiple local workers (2–4), not a cluster.

## Exit criteria (definition of done)
1. A high-level plan can be expanded into a deterministic OrchestrationPlan DAG.
2. The scheduler can run 2+ TaskRuns concurrently (bounded).
3. TaskRuns are executed via LangGraph (each has thread_id).
4. Interrupts work per task and appear in a unified Inbox.
5. Outputs from multiple tasks aggregate into a coherent review artifact:
   - preferred: one ChangesetBundle proposal per repo
   - acceptable: a small set of changeset bundles grouped by area
6. Concurrency quotas prevent resource exhaustion and GitHub rate-limit storms.
7. UI can show orchestration status at least minimally (read-only DAG view is enough in v9; v11 polishes it).

## Non-goals
- Full RAG memory (v10).
- Multi-user auth.
- SaaS multi-tenant billing.

## Key concepts (must be formalized)
### OrchestrationPlan
A deterministic representation of execution:
- tasks (nodes)
- dependencies (edges)
- per-task run specs (graph_id, budgets, tools, scope)
- aggregation instructions

### TaskSpec
A node template:
- goal/subgoal text
- input references (ContextPack, retrieval queries, prior task outputs)
- graph_id to execute
- budgets/tools_allowed

### TaskRun
A runtime instance:
- task_run_id
- task_id
- run_id (LangGraph-backed run)
- status, retries, lease
- outputs: artifact references

## Contracts (recommended to add in v9)
- `orchestration_plan/v1`
- `task_spec/v1`
- `task_run/v1`

If you do not add these contracts, the system will become opaque and hard to debug.

## Scheduler design (must be deterministic)
### Deterministic plan expansion
Given the same input plan/report + same repo snapshot, expansion must produce:
- stable task IDs
- stable dependency edges
- stable ordering for display and audit

Implementation rule:
- task_id = stable hash of (workspace_id, repo_id, plan_id, normalized title)
- dependencies sorted canonically

### Task lifecycle states (suggested)
- created
- waiting_for_deps
- waiting_for_approval
- runnable
- running
- blocked (interrupt)
- completed
- failed
- cancelled

### Approval semantics (must preserve invariants)
You have two viable patterns:

**Pattern A — Per-task approvals (simplest, safest)**
- each TaskRun requires a run approval before token spend

**Pattern B — Budget envelope approval (more ergonomic, more complex)**
- user approves an orchestration-level “budget envelope”
- tasks inherit token spend approval up to envelope limits
- still record per-task “approval derived from envelope” audit events

Recommendation for v9:
- start with Pattern A, then optionally add a “bulk approve selected tasks” UI action.

## Concurrency and quotas (non-negotiable)
Add explicit quotas:
- max parallel TaskRuns globally (e.g., 3)
- max parallel TaskRuns per repo (e.g., 2)
- max concurrent GitHub API calls (rate limiting)
- max concurrent test runs (if you have `run_tests` tool)
- max concurrent LLM calls (cost control)

Enforcement approach:
- scheduler selects runnable tasks in priority order
- dispatch only up to quota
- worker pool respects tool-level semaphores

## Output aggregation (make review human-friendly)
Goal: user reviews one (or a few) coherent bundles, not 20 random patches.

Aggregation strategy:
- each task produces either:
  - ChangesetBundle fragment (preferred), or
  - patch artifact + metadata
- aggregator groups fragments by repo and area:
  - merges into one ChangesetBundle per repo where possible
  - flags conflicts requiring human decision
- aggregator produces:
  - aggregated bundle artifact
  - summary report artifact (what changed, why, tests run)

Keep publish gate unchanged:
- humans approve changeset bundles before apply.

## Data model additions (control plane)
New tables/entities:
- orchestration_runs (orchestration_id, workspace_id, plan_id, status, created_at)
- task_specs (task_id, orchestration_id, spec_json, deps_json)
- task_runs (task_run_id, task_id, run_id, status, retries, lease fields)
- aggregation_runs (aggregation_id, orchestration_id, artifact_id, status)

## API surface (v9)
Orchestration:
- `POST /api/orchestrations` (create from plan/report)
- `GET /api/orchestrations/{id}` (status summary)
- `GET /api/orchestrations/{id}/dag` (nodes/edges + statuses)
- `POST /api/orchestrations/{id}/start` (creates TaskRuns)
- `POST /api/orchestrations/{id}/cancel`

Tasks:
- `GET /api/orchestrations/{id}/tasks`
- `POST /api/task-runs/{task_run_id}/approve` (or bulk approve endpoint)

Aggregation:
- `POST /api/orchestrations/{id}/aggregate` (manual trigger) or automatic
- `GET /api/orchestrations/{id}/artifacts`

Inbox:
- remains unified; now includes task-level run approvals and interrupts

## Worker model (v9)
Two worker types (both local):
1. **scheduler-worker**
   - expands plan → tasks
   - determines runnable tasks
   - enforces quotas
   - dispatches tasks (creates run records) and updates statuses

2. **execution-workers**
   - execute individual runs via LangGraphRunnerAdapter
   - handle interrupts, artifacts

Lease handling:
- scheduler leases TaskRuns for dispatch
- execution worker leases runs for execution

## Minimal UI needs (v9)
- orchestration list view (status: running/blocked/completed)
- DAG view (read-only ok):
  - nodes with status
  - click node → run detail
- bulk approve tasks (optional but very helpful)
- aggregated artifact review entry point

## Testing & evidence
- deterministic DAG expansion tests (same inputs → same DAG)
- quota enforcement tests (never exceed concurrency)
- integration test: 2 tasks run concurrently and complete producing 2 artifacts, then aggregation produces 1 bundle
- failure and retry tests with reason codes

## Rollout/rollback
Feature flags:
- `PMBOT_ENABLE_ORCHESTRATION`
- `PMBOT_ENABLE_SCHEDULER_WORKER`

Rollback:
- disable orchestration; single-run mode (v8) remains available
- do not delete orchestration history; keep audit intact

## Pitfalls
- If DAG expansion isn’t deterministic, debugging will be miserable.
- If quotas aren’t enforced, you will DDoS GitHub and burn tokens.
- If outputs aren’t aggregated, operators will drown in artifacts.

