# Data model

This spec defines a **local-first**, **single-human**, **multi-repo** data model for pm-bot.

Design targets:

- Works well on SQLite by default
- Keeps “big blobs” off the DB (filesystem artifact store)
- Supports multiple concurrent workers (with reasonable limits)
- Supports incremental GitHub sync (no rescans)
- Supports LangGraph execution via `thread_id`
- Supports RAG indexing later without committing to paid cloud services
- Can migrate to Postgres later with minimal pain

## Conceptual overview

pm-bot is a **control plane** that stores:

- what repos exist in a workspace
- what runs are happening
- what approvals/interrupts exist
- what artifacts were produced
- an audit log of everything

The execution plane (LangGraph) stores its heavy state (checkpoints) in filesystem (or a dedicated table if you choose), but the control plane always stores:

- `run_id` (canonical)
- `thread_id` (LangGraph thread)
- interrupt objects and decisions
- artifact metadata

## Workspaces

Even in single-user mode, you want a `workspace` concept.
It lets one instance manage multiple sets of repos cleanly:

- “phys-sims org” workspace
- “my personal repos” workspace
- “test workspace”

This is not multi-tenant SaaS. It’s just structure.

## Minimal tables

### 1) workspaces

Purpose: group repos + runs.

Key fields:
- `workspace_id` (PK)
- `name`
- `created_at`
- `settings_json` (budgets defaults, polling intervals, etc.)

### 2) repos

Purpose: register repos under management.

Key fields:
- `repo_id` (PK)
- `workspace_id` (FK)
- `full_name` (owner/repo)
- `default_branch`
- `status` (active/disabled)
- `added_at`
- `last_sync_at`

Indexes:
- `(workspace_id, full_name)` unique

### 3) repo_sync_state

Purpose: track incremental sync cursors.

Key fields:
- `repo_id` (PK/FK)
- `issues_cursor_updated_at` (timestamp)
- `prs_cursor_updated_at` (timestamp)
- `repo_head_sha` (last known default branch head)
- `last_indexed_sha` (for code/doc indexing)
- `last_error` (string)
- `updated_at`

### 4) github_objects (cache)

Purpose: store issues/PRs/discussions with minimal schema churn.

Recommended approach for early-stage:
- store raw JSON for each object
- store a few indexed columns for filtering/search

Key fields:
- `object_id` (PK)
- `repo_id` (FK)
- `kind` (issue/pr)
- `number` (int)
- `title` (text)
- `state` (text)
- `updated_at` (timestamp)
- `raw_json` (text)

Indexes:
- `(repo_id, kind, number)` unique
- `(repo_id, kind, updated_at)` for incremental refresh

Rationale:
- You avoid schema churn as GitHub payloads evolve.
- You can always normalize later if needed.

### 5) runs

Purpose: canonical lifecycle for an agent run.

Key fields:
- `run_id` (PK)
- `workspace_id` (FK)
- `repo_id` (FK)
- `goal` (text)
- `status` (enum-ish text)
- `graph_id` (e.g., repo_change_proposer/v1)
- `thread_id` (LangGraph thread id; nullable until submit)
- `agent_run_spec_json` (the full spec; text)
- `created_at`, `updated_at`

Recommended statuses:
- proposed
- approved
- running
- blocked
- completed
- failed
- cancelled
- rejected

Indexes:
- `(workspace_id, status, updated_at)`
- `(repo_id, status, updated_at)`

### 6) approvals

Purpose: explicit human gates.

Key fields:
- `approval_id` (PK)
- `run_id` (FK)
- `kind` (run_start, tool_call, spend, publish, changeset_apply)
- `status` (pending/approved/rejected)
- `created_at`, `resolved_at`
- `actor` (string) — single-user mode can store “local_user”
- `notes` (text)

Index:
- `(run_id, kind, status)`

### 7) interrupts

Purpose: store LangGraph/agent interrupts as Inbox items.

Key fields:
- `interrupt_id` (PK)
- `run_id` (FK)
- `thread_id` (text)
- `kind` (approve_tool_call / approve_spend / approve_publish / question)
- `risk` (low/medium/high)
- `payload_json` (text; redacted)
- `status` (pending/approved/rejected/edited)
- `decision_json` (text)
- `created_at`, `resolved_at`

Indexes:
- `(workspace_id, status, created_at)` via join on runs.workspace_id
- `(run_id, status)`

### 8) artifacts

Purpose: store metadata for any run output.

Key fields:
- `artifact_id` (PK)
- `run_id` (FK)
- `kind` (changeset_bundle, patch, log, tool_trace, test_report, pr_draft)
- `uri` (text) — filesystem path or db:// pointer
- `content_type` (text)
- `hash` (text)
- `title` (text)
- `created_at`

Index:
- `(run_id, kind, created_at)`

### 9) changeset_bundles

Purpose: first-class representation for proposed repo mutations.

Key fields:
- `changeset_id` (PK)
- `run_id` (FK)
- `repo_id` (FK)
- `bundle_json` (text)
- `status` (proposed/approved/applied/rejected)
- `created_at`, `updated_at`
- `applied_commit_sha` (nullable)

Indexes:
- `(repo_id, status, updated_at)`

### 10) audit_events

Purpose: append-only audit log.

Key fields:
- `event_id` (PK)
- `workspace_id` (FK)
- `run_id` (nullable)
- `thread_id` (nullable)
- `node_id` (nullable)
- `type` (text)
- `payload_json` (text; redacted)
- `created_at`

Optional tamper-evidence:
- `prev_hash` / `hash`

Indexes:
- `(run_id, created_at)`
- `(workspace_id, created_at)`

## Checkpoints and tool transcripts

### Recommended (SQLite-friendly)

- checkpoints stored on filesystem:
  - `data/checkpoints/<thread_id>/checkpoint_<n>.json`
- tool transcripts stored as artifacts:
  - `data/artifacts/<run_id>/tool_trace.jsonl`

DB stores only:
- pointers/URIs
- metadata

This keeps DB writes small and reduces lock contention.

## RAG metadata tables (v10)

Vectors can live in a local vector DB (e.g., Qdrant). The control plane DB should still store metadata for:
- provenance
- snapshotting
- reproducibility

### documents

- `doc_id` (PK)
- `workspace_id`
- `repo_id`
- `source_type` (file/issue/pr)
- `source_id` (path or URL)
- `revision` (commit SHA or timestamp)
- `content_hash`
- `created_at`

### chunks

- `chunk_id` (PK)
- `doc_id` (FK)
- `ordinal` (int)
- `start_offset` / `end_offset` (line numbers or byte offsets)
- `text_hash`
- `token_count`

### embedding_records

- `embedding_id` (PK)
- `chunk_id` (FK)
- `vector_store` (qdrant)
- `vector_point_id` (string)
- `embedding_model` (string)
- `created_at`

### ingestion_jobs

- `job_id` (PK)
- `workspace_id`
- `repo_id`
- `kind` (full / incremental)
- `status`
- `stats_json`
- `error`
- timestamps

## SQLite operational requirements

If you want multiple local workers, set these pragmas:

- `journal_mode=WAL`
- `synchronous=NORMAL`
- `busy_timeout=5000` (or more)

And follow these rules:

- keep transactions short
- do not write big blobs into DB
- prefer append-only small audit rows

## Migration to Postgres

Design for portability:

- avoid SQLite-only SQL features
- store JSON as text if your ORM supports both
- keep IDs as strings/UUIDs

When you switch:
- keep the filesystem artifact store the same
- only the control-plane DB changes

## Suggested SQL skeleton (optional)

If you want a starting point, you can generate SQL from your ORM.
Avoid hand-writing vendor-specific DDL unless you commit to Postgres.

The important part is the shape and invariants above.
