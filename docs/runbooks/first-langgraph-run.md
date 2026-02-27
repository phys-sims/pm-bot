# Runbook: First LangGraph repo_change_proposer run
> **Audience:** Operators validating end-to-end LangGraph run execution.
> **Depth:** L1 (procedural verification).
> **Source of truth:** Local validation flow for `repo_change_proposer/v1` that emits a ChangesetBundle artifact.

This runbook proves end-to-end value for the first LangGraph graph by showing that an approved run produces a reviewable ChangesetBundle artifact that is visible in API/UI run details.

## Preconditions

- Install dependencies:

```bash
pip install -e ".[dev]"
```

- Start backend API:

```bash
uvicorn pm_bot.server.app:app --host 127.0.0.1 --port 8000
```

- Optional UI (for visual verification):

```bash
cd ui
npm install
npm run dev -- --host 127.0.0.1 --port 4173
```

## Step 1: Create a LangGraph run

```bash
curl -s -X POST http://127.0.0.1:8000/agent-runs \
  -H 'content-type: application/json' \
  -d '{
    "created_by": "human",
    "spec": {
      "schema_version": "agent_run_spec/v2",
      "run_id": "run-local-repo-change-1",
      "goal": "Propose repository changes for review",
      "inputs": {
        "context_pack_id": "ctx-local-1",
        "context_pack": {
          "schema_version": "context_pack/v2",
          "root": {"issue_ref": "phys-sims/pm-bot#123"}
        },
        "issue_ref": "#123",
        "diff": {
          "status_changes": [
            {"issue_ref": "#123", "before": "Backlog", "after": "In Progress"}
          ],
          "blocker_changes": []
        }
      },
      "execution": {
        "engine": "langgraph",
        "graph_id": "repo_change_proposer/v1",
        "thread_id": null,
        "budget": {
          "max_total_tokens": 2000,
          "max_tool_calls": 10,
          "max_wall_seconds": 300
        },
        "tools_allowed": ["github_read"],
        "scopes": {"repo": "phys-sims/pm-bot"}
      },
      "model": "gpt-5",
      "intent": "repo_change_proposer",
      "requires_approval": true,
      "adapter": "langgraph"
    }
  }'
```

## Step 2: Approve run

```bash
curl -s -X POST http://127.0.0.1:8000/runs/run-local-repo-change-1/approve \
  -H 'content-type: application/json' \
  -d '{"actor": "reviewer"}'
```

## Step 3: Claim and execute until completed

```bash
curl -s -X POST http://127.0.0.1:8000/agent-runs/claim \
  -H 'content-type: application/json' \
  -d '{"worker_id": "w1", "limit": 1, "lease_seconds": 60}'
```

```bash
curl -s -X POST http://127.0.0.1:8000/agent-runs/execute \
  -H 'content-type: application/json' \
  -d '{"run_id": "run-local-repo-change-1", "worker_id": "w1"}'
```

Run the `claim` + `execute` pair repeatedly until run status is `completed`.

## Step 4: Validate artifact visibility in API

```bash
curl -s http://127.0.0.1:8000/runs/run-local-repo-change-1
```

Expected:
- `status` is `completed`.
- `artifacts` contains one artifact URI ending with `.changeset_bundle.json`.

## Step 5: Validate artifact visibility in UI

- Open the UI and navigate to run details.
- Locate run `run-local-repo-change-1`.
- Confirm the artifact entry is visible and points to the emitted ChangesetBundle file.

## Safety and policy expectations

- This graph does not perform GitHub writes.
- Context loading is cache/context-pack first.
- Any expensive external action request (`repo_checkout`, `run_tests`) triggers an interrupt unless explicitly approved in input (`allow_expensive_actions=true`).
