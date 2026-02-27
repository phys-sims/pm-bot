# Contract: AgentRunSpec/v2

This document defines **AgentRunSpec/v2**, the input specification for launching an agent run in pm-bot.

v2 extends earlier versions by adding explicit **execution backend configuration** (LangGraph) and durable execution metadata (**thread_id**).

---

## Purpose

An AgentRunSpec is the *approval-gated* request to execute an agent run. It is designed to be:

- **Auditable**: every run can be traced to a spec and approvals.
- **Policy-first**: budgets and tool allowlists are explicit.
- **Backend-agnostic (future)**: this version introduces `execution.engine`, which can later support other runtimes, but v2 standardizes on LangGraph.

---

## Core invariants (must hold)

- **No model calls without approval.**
- **No external side effects without policy/approval.**
- **No GitHub writes without an approved ChangesetBundle (or equivalent gated publish artifact).**
- **Audit is append-only and correlated by run_id and thread_id.**

---

## Schema (logical)

### Top-level fields

- `run_id` (uuid, required): globally unique identifier for the run.
- `goal` (string, required): the human-readable objective.
- `inputs` (object, required): references to the deterministic inputs (usually a ContextPack id).

### Execution configuration

`execution` (object, required)

- `engine` (string, required): for v2 must be `"langgraph"`.
- `graph_id` (string, required): versioned identifier of the canonical LangGraph to execute (e.g. `"repo_change_proposer/v1"`).
- `thread_id` (string | null, optional): assigned when execution begins; durable pointer for checkpoints/interrupt resume.
- `budget` (object, required):
  - `max_total_tokens` (int, required)
  - `max_tool_calls` (int, required)
  - `max_wall_seconds` (int, required)
- `tools_allowed` (array[string], required): allowlist of tools that may be invoked (any tool not in this list must be denied or require an interrupt).
- `scopes` (object, required):
  - `repo` (string, required): `owner/repo` allowed for read access and for *proposal* artifacts.

---

## Example (JSON)

```json
{
  "run_id": "2c8a0a3a-3c1a-4e6f-86e5-8573ef9f2a3c",
  "goal": "Propose a safe changeset bundle implementing feature X",
  "inputs": {
    "context_pack_id": "ctx_123"
  },
  "execution": {
    "engine": "langgraph",
    "graph_id": "repo_change_proposer/v1",
    "thread_id": null,
    "budget": {
      "max_total_tokens": 200000,
      "max_tool_calls": 50,
      "max_wall_seconds": 1800
    },
    "tools_allowed": [
      "github_read",
      "repo_checkout",
      "pytest",
      "retrieval_query"
    ],
    "scopes": {
      "repo": "phys-sims/pm-bot"
    }
  }
}
```

---

## Semantics

### Approval gating

- A run spec must be approved before the execution engine may:
  - call any LLM provider
  - call any external tool
  - emit publish artifacts (e.g., PR drafts)

### Budgets

Budgets apply to the whole run (all nodes, all retries). The execution engine must:

- stop/fail closed when budgets are exceeded, OR
- raise an interrupt requesting explicit approval to extend a budget.

### Tool allowlist

The execution engine must enforce:

- tool calls not listed in `tools_allowed` are blocked (interrupt or hard-deny).
- tool call arguments must be redacted in interrupt payloads and audit logs.

### Thread ID lifecycle

- `thread_id` is created when execution begins.
- control plane persists `thread_id` so:
  - interrupts can be resumed
  - the UI can correlate status
  - audit can correlate events

---

## Compatibility guidance

- Clients should ignore unknown fields (forward compatibility).
- If you currently have a v1 AgentRunSpec:
  - you can support both by storing `execution` as optional for v1 and required for v2,
  - or migrate everything to v2 with a database migration and a coercion layer.

---

## Notes for implementers

- Do not encode runtime-specific options (like LangGraph internal node names) into the contract.
- Use semantic, versioned `graph_id` values:
  - `repo_change_proposer/v1`
  - `task_run_executor/v1`
  - `retrieval_augmented_proposer/v1`
