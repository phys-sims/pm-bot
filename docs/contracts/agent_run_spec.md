# AgentRunSpec
> **Audience:** Contributors implementing agent execution planning and controls.
> **Depth:** L3 (normative contract).
> **Source of truth:** Authoritative contract semantics for AgentRunSpec and guardrails.


AgentRunSpec is the contract for proposing and executing LLM-powered agent runs safely.

It exists to enforce two non-negotiables:

1. **No token spend without approval**
2. **No privileged writes from an agent step**

An agent run should typically produce:

- a proposed ChangesetBundle (for you to approve), and/or
- a draft PR (for you to review)

## Design goals

AgentRunSpec MUST:

- be explicit about cost controls (token budget, model)
- be explicit about allowed outputs (what the agent can propose)
- be approval-gated before execution
- bind to a specific context pack version/hash to ensure determinism

AgentRunSpec SHOULD:

- support a “manual execution” mode (generate a pasteable prompt bundle)
- support “dry-run estimation” of cost where possible

## Core fields (recommended)

- `schema_version` (required): `agent_run_spec/v1`
- `run_id` (string, required): unique identifier
- `created_at` (datetime, required)
- `created_by` (string, required): user or agent id
- `status` (enum, required):
  - `proposed | approved | rejected | running | completed | failed | cancelled`
- `requires_approval` (bool, required): true

### Target and scope

- `target` (object, required):
  - `org` (string)
  - `repo` (string, optional): if scoped to a repo
  - `work_item_ids` (array[string], required): stable_ids involved
- `intent` (string, required): short description (“Implement estimator v1”, “Draft PR for issue #123”)

### Context pack binding

- `context_pack` (object, required):
  - `pack_id` (string)
  - `hash` (string): content hash
  - `version` (string): context pack format version
  - `inputs` (array): list of work item IDs / issue URLs included


### Audit linkage (v4+)

When runs request context building, audit events SHOULD include:

- `event_type`: `context_pack_built`
- `run_id`: copied from AgentRunSpec
- context hash + budget summary
- requesting actor (`requested_by`)

This enables run-level traceability from agent run proposal through context build and downstream changeset/report artifacts.

### Model and budget

- `model` (string, required): e.g. `gpt-5`, `gpt-4.1`, etc (your choice)
- `max_tokens` (int, required)
- `temperature` (number, optional)
- `cost_estimate` (object, optional):
  - `estimated_input_tokens`
  - `estimated_output_tokens`
  - `estimated_usd` (optional)

### Tooling and permissions

- `tools_allowed` (array[string], required):
  - e.g. `none`, `filesystem_read`, `git_read`, `git_write_propose`, `github_read`
- `outputs_allowed` (array[string], required):
  - `propose_changeset_bundle`
  - `propose_pr`
  - `propose_issue_comment`
  - `propose_test_plan`

**Important:** even if `propose_pr` is allowed, the agent MUST NOT merge or publish without a human action.

### Result binding

- `result` (object, optional):
  - `changeset_bundle_id` (string, optional)
  - `draft_pr_url` (string, optional)
  - `artifact_paths` (array[string], optional)
  - `summary` (string, optional)


## Runner lifecycle + queue semantics (v5 / Task C)

### Normalized statuses

- `proposed`
- `approved`
- `running`
- `completed` (terminal)
- `failed` (terminal unless explicitly re-approved)
- `cancelled` (terminal)
- `rejected` (terminal)

### Allowed transitions

- `proposed -> approved | rejected | cancelled`
- `approved -> running | cancelled`
- `running -> completed | failed | cancelled | approved` (approved is retry scheduling)
- `failed -> approved | cancelled`

Invalid transitions MUST be rejected with deterministic reason codes.

### Queue/claim metadata

AgentRunSpec-backed execution records SHOULD include bounded local worker queue fields:

- `claimed_by` (worker identifier)
- `claim_expires_at` (lease expiry timestamp)
- `retry_count`
- `max_retries`
- `next_attempt_at`
- `last_error`
- `job_id` (adapter-specific submission handle)

### Adapter contract

Runners MUST support an adapter interface with the following operations:

- `submit(run) -> {job_id, state}`
- `poll(run) -> {state, reason_code?}`
- `fetch_artifacts(run) -> [path, ...]`
- `cancel(run) -> {state, reason_code?}`

The default adapter is `manual` for local deterministic execution. Any additional provider adapters MUST map failures to deterministic shared reason codes.

## Execution policy (normative)

- AgentRunSpecs MUST be approved before execution.
- Agent runs MUST NOT have direct access to privileged GitHub tokens that can mutate Projects/Issues.
- If an agent proposes changes, it MUST do so via:
  - a ChangesetBundle, OR
  - a draft PR

Both require human review.

## Manual mode

pm-bot SHOULD support a manual mode where the AgentRunSpec results in:

- a deterministic “prompt bundle” (context pack + instructions)
- the user runs it in an external tool
- the user pastes the result back for conversion into changesets/PRs

This enables adoption even before full API-driven orchestration exists.

## Example AgentRunSpec

```json
{
  "schema_version": "agent_run_spec/v1",
  "run_id": "agent_run_2026-02-22_0003",
  "created_at": "2026-02-22T01:10:00Z",
  "created_by": "@you",
  "status": "proposed",
  "requires_approval": true,
  "target": {
    "org": "phys-sims",
    "repo": "pm-bot",
    "work_item_ids": ["feat:contracts"]
  },
  "intent": "Draft docs/contracts pages and examples",
  "context_pack": {
    "pack_id": "cp_0009",
    "hash": "sha256:abcd...",
    "version": "context_pack/v1",
    "inputs": ["feat:contracts"]
  },
  "model": "gpt-5",
  "max_tokens": 12000,
  "temperature": 0.2,
  "tools_allowed": ["filesystem_read"],
  "outputs_allowed": ["propose_changeset_bundle", "propose_pr"]
}
```

