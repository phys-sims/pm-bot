# HTTP API surface index
> **Audience:** Operators and agents needing quick route discoverability.
> **Depth:** L2 (behavior/integration index).
> **Source of truth:** Compact index of implemented ASGI routes; authoritative behavior lives in linked specs/contracts.

## Usage notes

- This index is discoverability-only.
- If this page conflicts with domain specs/contracts, linked L2/L3 docs win.
- Route implementation source: `pm_bot/server/app.py`.

## Core health and triage

- `GET /health` → process liveness response (`status=ok`).
- `GET /inbox` → unified inbox contract and ordering rules: [`docs/spec/inbox.md`](inbox.md).

## Runs + interrupts

- `POST /runs` → create a proposed LangGraph run using AgentRunSpec v2 semantics.
- `POST /runs/{id}/approve` → approve run start (transitions to `approved`).
- `GET /runs/{id}` → retrieve run status with thread/artifacts/interrupts.
- `POST /interrupts/{id}/resolve` → resolve pending interrupt (`approve|reject|edit`).

## Changesets

- `GET /changesets/pending` → pending approval queue summary: [`docs/contracts/changesets.md`](../contracts/changesets.md).
- `POST /changesets/propose` → propose approval-gated write intent: [`docs/contracts/changesets.md`](../contracts/changesets.md).
- `POST /changesets/{id}/approve` → human approval + guarded apply path: [`docs/contracts/changesets.md`](../contracts/changesets.md).

## Graph and estimation

- `GET /graph/tree` → hierarchy view + provenance semantics: [`docs/spec/graph-api.md`](graph-api.md), [`docs/contracts/workgraph.md`](../contracts/workgraph.md).
- `GET /graph/deps` → dependency view + diagnostics semantics: [`docs/spec/graph-api.md`](graph-api.md).
- `POST /graph/ingest` → graph ingestion and partial-failure diagnostics: [`docs/spec/graph-api.md`](graph-api.md).
- `GET /estimator/snapshot` → estimator snapshot retrieval and fallback semantics: [`docs/spec/estimator.md`](estimator.md).

## Reports and context

- `GET /reports/weekly/latest` → latest generated weekly report path and reporting metrics context: [`docs/spec/reporting.md`](reporting.md).
- `GET /context-pack` → context pack builder surface, including optional retrieval augmentation (`retrieval_query`, repo scope, doc_type allowlist): [`docs/contracts/context_pack.md`](../contracts/context_pack.md).

## RAG retrieval

- `POST /rag/index` → index docs corpus for retrieval.
- `GET /rag/status` → latest indexing status/statistics.
- `GET /rag/query` → legacy query surface (`q`, `limit`).
- `POST /rag/query` → retrieval query body (`repo_id`, `query`, `filters.doc_types`, `top_k`) with deterministic ordering by score bucket and chunk id.

## Agent-run orchestration

- `POST /agent-runs/propose` → create run proposal: [`docs/contracts/agent_run_spec.md`](../contracts/agent_run_spec.md).
- `POST /agent-runs/transition` → deterministic status transition guardrails: [`docs/contracts/agent_run_spec.md`](../contracts/agent_run_spec.md).
- `POST /agent-runs/claim` → worker claim semantics: [`docs/contracts/agent_run_spec.md`](../contracts/agent_run_spec.md).
- `POST /agent-runs/execute` → execute claimed run and emit audit outcomes: [`docs/contracts/agent_run_spec.md`](../contracts/agent_run_spec.md).
- `GET /agent-runs/transitions` → transition history retrieval: [`docs/contracts/agent_run_spec.md`](../contracts/agent_run_spec.md).
- `POST /agent-runs/cancel` → cancellation policy and audit behavior: [`docs/contracts/agent_run_spec.md`](../contracts/agent_run_spec.md).

## Onboarding readiness

- `GET /onboarding/readiness` → persisted readiness state: [`docs/spec/inbox.md`](inbox.md#onboarding-readiness-api-hooks-v5).
- `POST /onboarding/dry-run` → non-mutating readiness evaluation: [`docs/spec/inbox.md`](inbox.md#onboarding-readiness-api-hooks-v5).

## Audit and incident outputs

- `GET /audit/chain` → filtered audit event chain contract: [`docs/spec/reporting.md`](reporting.md).
- `GET /audit/rollups` → run-level rollups and concentration metrics: [`docs/spec/reporting.md`](reporting.md).
- `GET /audit/incident-bundle` → bounded incident evidence bundle: [`docs/spec/reporting.md`](reporting.md).

## ReportIR workflow

- `POST /report-ir/intake`
- `POST /report-ir/confirm`
- `POST /report-ir/preview`
- `POST /report-ir/propose`

Authoritative route semantics: [`docs/spec/report-ir-api.md`](report-ir-api.md).


## Repo registry and cache sync

- `POST /repos/add` → register repo and trigger initial cache import (issues + PRs).
- `POST /repos/{id}/sync` → manual incremental refresh for one repo.
- `GET /repos` → list registered repos + sync/index status/error fields.
- `GET /repos/search?q=<text>` → search/select candidate repos from connector allowlist and show already-added state.
- `GET /repos/{id}/status` → sync/index timestamps + cached issue/PR counts for progress UI.
- `POST /repos/reindex-docs` → trigger docs reindex (optionally repo-scoped with `repo_id`).
- `POST /repos/{id}/reindex` → trigger repo reindex shortcut for dashboard action.
- `GET /repos/{id}/issues` → cached issue rows for repo.
- `GET /repos/{id}/prs` → cached PR rows for repo.

## Internal flow reference (non-HTTP)

- Board snapshot + replanner orchestration behavior: [`docs/spec/board-replanner.md`](board-replanner.md).
