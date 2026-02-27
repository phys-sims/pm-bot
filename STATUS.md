# Project Status (pm-bot)

> **Source of truth:** Update this file whenever behavior, tests, schemas, workflows, or canonical inputs change.
> **Agent rule:** Keep entries current and prune stale content in the same change.
> **Date integrity rule:** Populate dates/times with runtime commands (for example `date -u`); never guess dates.

## Last updated
- Date: 2026-02-27
- Time (UTC): 07:09:17 UTC
- By: @openai-codex

---

## CI health checklist

| Check | Command | Status | Last run | Notes |
| --- | --- | --- | --- | --- |
| Tests | `pytest -q` | ✅ | 2026-02-27 | Core suites cover parser/rendering, server behavior, contracts, and docs hygiene. |
| Lint | `ruff check .` | ✅ | 2026-02-27 | No lint violations. |
| Format | `ruff format .` | ✅ | 2026-02-27 | Formatting is stable. |
| Docs hygiene | `python scripts/docs_hygiene.py --check-links --check-contradictions --check-status-gates --check-depth-metadata --check-l0-bloat` | ✅ | 2026-02-27 | Validates markdown links, docs-governance workflow references, status-shape gates, and L0/depth metadata limits. |
| Package install | `pip install -e ".[dev]"` | ⬜ | — | Validate in clean environment if needed. |
| Docker Compose config | `docker compose config` | ✅ (CI) / ⚠️ (local env) | 2026-02-25 | CI validates compose; local shell in this environment may not include Docker CLI. |

---

## Current compatibility notes

- Canonical inputs:
  - `vendor/dotgithub/ISSUE_TEMPLATE/*.yml`
  - `vendor/dotgithub/issue-templates-guide.md`
  - `vendor/dotgithub/project-field-sync.yml`
  - `pm_bot/schema/work_item.schema.json`
- Required tracked headings/labels for project sync:
  `Area`, `Priority`, `Size`, `Estimate (hrs)`, `Risk`, `Blocked by`, `Actual (hrs)`.
- Known compatibility shim:
  Epic template currently uses `Size (Epic)`; parser compatibility shim is implemented and renderer normalizes to `Size`.

---

## Active change scope bullets

> **Template + stale content pruning instructions:**
> - Keep only bullets for currently active/recently landed changes that still describe repository reality.
> - Remove superseded bullets in the same PR that introduces replacement behavior/docs/tests.
> - Do not keep historical roadmap narratives/checklists here; place durable planning content in `docs/roadmaps/` (active) or `docs/archive/roadmaps/` (historical).

- Added unified approvals UI flow: Inbox now deterministically surfaces run-start approvals, interrupts (approve/edit/reject), and changeset approvals with explicit action states; new Run Detail page shows run status + budget consumption, artifact viewers (diff/log/json/text), and ordered interrupt/audit timeline controls including interrupt approve→resume and changeset apply approval paths.
- Fixed unified-inbox/run-detail follow-up regressions: UI tests now isolate DOM per test to avoid duplicate empty-state assertions, run-detail success messaging persists after approve+refresh, and backend artifact view now resolves artifact root via storage settings (restoring lint + CI front-end test expectations).
- Fixed interrupt edit resume payload forwarding: Inbox now resumes edited interrupts with the resolved decision payload (`decision.edited_payload`) so LangGraph resume receives user edits instead of `{}` defaults, with UI test coverage asserting the exact resume request body.
- Added local-first onboarding + repo sync dashboard support: UI now guides token mode, repo search/select, and initial sync progress, while backend adds repo search/status and reindex endpoints plus `last_index_at` tracking for dashboard visibility and no-DB-poking setup flows; app default landing remains Inbox for test/runtime compatibility.
- Added optional retrieval path to `repo_change_proposer/v1`: planner now deterministically decides whether to retrieve, retrieval chunks are budget-bounded (`max_retrieval_tokens`) before insertion into context-pack `retrieved` sections and manifest metadata, and retrieval query/chunk-id provenance is emitted to audit and persisted in run artifacts.
- Added local RAG bootstrap support: Docker Compose now includes a persistent `qdrant` service (`./data/qdrant`), control-plane retriever abstraction stubs (`embed/upsert/query`), and SQLite metadata tables for `documents`, `chunks`, `embedding_records`, and `ingestion_jobs`.
- Added docs-governance RAG ingestion pipeline and APIs: `/rag/index` launches indexing over `docs/spec/*`, `docs/contracts/*`, and `docs/adr/*`; stable chunk IDs now hash source path + revision + line range, chunk provenance (line_start/line_end, source_path, doc_type, revision_sha) is persisted and returned by `/rag/query`, and ingestion status is exposed via `/rag/status` with idempotent upsert behavior across repeated same-revision indexing.
- Added retrieval usability/auditability upgrades: `POST /rag/query` now supports repo-scoped and doc_type-allowlisted filters with deterministic result ordering (score bucket + chunk_id), ContextPack v2 can include explicit `retrieved` sections with provenance and `manifest.retrieval.chunk_ids`, and a golden-snapshot regression harness validates retrieval outputs against fixed expected chunk IDs.
- Added LangGraph runner adapter wiring with submit/poll/resume/cancel/fetch behavior, including blocked interrupt polling and resume auditing.
- Added filesystem+DB checkpoint bridge: checkpoint blobs are persisted under `data/checkpoints/<thread_id>/` and run checkpoint metadata is persisted in `run_checkpoint_metadata`.
- Added LangGraph policy enforcement (tool allowlist + token/tool/wall budgets) with configurable violation mode (`interrupt` default, `fail` override) and audit emission for model/tool/interrupt events.
- Implemented `repo_change_proposer/v1` LangGraph flow with `load_context_pack`, `propose_changeset_bundle` (strict capability schema validation), and `emit_artifact` that writes filesystem artifacts and persists DB artifact metadata for run visibility.
- Added policy interrupt before expensive external actions (`repo_checkout`, `run_tests`) unless explicitly allowed in run inputs; graph remains no-GitHub-write.
- Expanded runner tests to assert unapproved runs execute no model/tool calls, approved repo-change runs emit ChangesetBundle artifacts, audit logs include `run_id` + `thread_id` for model calls, and GitHub write endpoints are not invoked.
- Added orchestration planning contracts (`orchestration_plan/v1`, `task_spec/v1`, `task_run/v1`), deterministic plan expansion, storage tables (`orchestration_plan`, `task_runs`, `task_edges`), and `/plans/<id>/expand` + `/plans/<id>/dag` APIs with deterministic snapshot coverage.
- Stabilized UI integration coverage for Plan Intake to Inbox approval/apply flow by enforcing per-test DOM cleanup and aligning the App-level assertion with InboxPage behavior (post-approve refresh clears transient status and shows empty-state), while keeping the runbook metadata contract compliant with docs hygiene gates.
- Added a lease-based TaskRun scheduler loop with dependency-aware runnable selection, per-repo/tool/provider concurrency quotas, deterministic retries (`retries` + `next_attempt_at`), and task-level reason-code/audit correlation (`task_run_id` + `run_id` + `thread_id`).
- Added orchestration artifact aggregation (`/plans/<id>/aggregate`) that gathers task `*.changeset_bundle.json` artifacts into one reviewable aggregated proposal, links it on plan DAG payloads, and emits conflict interrupts when task bundles propose conflicting mutations.
