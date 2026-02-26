# Org-scale execution task cards (agent-editable)

_Source doc (archived): `docs/archive/roadmaps/org-scale-roadmap-reconciliation.md`_

This file is intended for agent/operator updates while the reconciliation roadmap remains stable source-of-truth planning.

## Implemented execution plan cards (all track phases)

The following cards instantiate every phase in Tracks A–D using the task template above.

### Task: A1 — Graph identity model extension

**Objective**
- Additive graph storage for org/repo/node identity and typed-edge metadata without breaking existing `graph_tree` and `graph_deps` callers.

**Pre-flight checks**
- [x] Link repo inventory section 3 + 4 for DB and graph baselines.
- [x] Confirm migration pattern in `pm_bot/server/db.py` remains additive and boot-safe.

**Safety constraints**
- [x] Approval gate preserved.
- [x] Runner has no GitHub write token access.
- [x] Deterministic ordering/hash behavior maintained.
- [x] Idempotent retry behavior preserved or improved.

**Implementation steps**
1. Introduce additive tables/views for stable node identity (`org`, `repo`, `node_id`) and typed edges.
2. Wire tree/dependency reads directly to typed graph edges.
3. Add deterministic unique constraints/indexes for edge provenance records.

**Likely files touched**
- `pm_bot/server/db.py`
- `pm_bot/server/graph.py`
- `docs/contracts/workgraph.md`
- `tests/test_v2_graph.py`

**Tests**
- Unit: DB upsert/read for graph identity + typed graph rows.
- Integration: graph service returns unchanged trees for legacy fixtures.
- HTTP/UI: `/graph/tree` contract snapshot remains stable.

**Acceptance criteria**
- Existing graph APIs stay backward-compatible while storing stable cross-repo identity.

**Rollback**
- Disable new tables/views reads and continue serving legacy relationship model.

### Task: A2 — Graph ingestion expansion

**Objective**
- Expand connector ingestion to collect GitHub sub-issue/dependency edges with provenance and diagnostics counters.

**Pre-flight checks**
- [x] Link repo inventory section 6 for connector surfaces.
- [x] Confirm budget/rate-limit guardrails from auth/token docs.

**Safety constraints**
- [x] Approval gate preserved.
- [x] Runner has no GitHub write token access.
- [x] Deterministic ordering/hash behavior maintained.
- [x] Idempotent retry behavior preserved or improved.

**Implementation steps**
1. Add read-only connector methods for sub-issues/dependencies.
2. Persist ingestion diagnostics (`calls`, `failures`, `partial=true/false`).
3. Record edge provenance source and timestamp for replay/debugging.

**Likely files touched**
- `pm_bot/server/github_connector_api.py`
- `pm_bot/server/graph.py`
- `pm_bot/server/db.py`
- `tests/test_github_connector_api.py`

**Tests**
- Unit: connector response normalization for edge endpoint payload variants.
- Integration: partial ingestion yields diagnostics warnings without failing full sync.
- HTTP/UI: graph dependency endpoint returns provenance warnings deterministically.

**Acceptance criteria**
- Ingestion captures typed edges and emits diagnostics snapshots with call-budget accounting.

**Rollback**
- Revert connector edge polling and serve prior checklist/dependency-only ingestion.

### Task: A3 — Deterministic graph reconciliation

**Objective**
- Deterministic ordering, cycle warnings, and partial-ingestion reason codes at the graph API boundary.

**Pre-flight checks**
- [x] Confirm existing ordering behavior in graph tests.
- [x] Confirm reason-code conventions in changeset denial paths for consistency.

**Safety constraints**
- [x] Approval gate preserved.
- [x] Runner has no GitHub write token access.
- [x] Deterministic ordering/hash behavior maintained.
- [x] Idempotent retry behavior preserved or improved.

**Implementation steps**
1. Add canonical node/edge sort keys.
2. Emit explicit warnings for detected cycles and partial ingestion.
3. Surface machine-readable reconciliation reason codes in API payloads.

**Likely files touched**
- `pm_bot/server/graph.py`
- `pm_bot/server/app.py`
- `docs/spec/graph-api.md`
- `tests/test_server_http_contract.py`

**Tests**
- Unit: reconciliation sorts consistently independent of insertion order.
- Integration: cycle scenarios emit stable warnings.
- HTTP/UI: response JSON includes deterministic warning/reason fields.

**Acceptance criteria**
- Identical DB state always yields byte-stable graph payload ordering plus explicit warning metadata.

**Rollback**
- Remove new warning envelope fields while keeping existing graph responses intact.

### Task: B1 — Context pack v2 schema + hash contract

**Objective**
- Add `context_pack/v2` schema with canonical serialization and stable hash computation rules.

**Pre-flight checks**
- [x] Link repo inventory section 4 for context pack/AgentRunSpec surfaces.
- [x] Confirm existing hash behavior in `pm_bot/server/context_pack.py`.

**Safety constraints**
- [x] Approval gate preserved.
- [x] Runner has no GitHub write token access.
- [x] Deterministic ordering/hash behavior maintained.
- [x] Idempotent retry behavior preserved or improved.

**Implementation steps**
1. Define v2 schema artifact and versioned payload envelope.
2. Implement canonical JSON serialization rules (field order, whitespace, encoding).
3. Add compatibility mapper from v1 payloads where needed.

**Likely files touched**
- `pm_bot/schema/context_pack_v2.schema.json`
- `pm_bot/server/context_pack.py`
- `docs/contracts/context_pack.md`
- `tests/test_v1_server.py`

**Tests**
- Unit: canonicalization invariants and hash reproducibility.
- Integration: repeated builds produce identical hashes for identical inputs.
- HTTP/UI: context-pack route continues honoring budget input with versioned output.

**Acceptance criteria**
- Context pack v2 output is schema-valid and hash-stable across reruns.

**Rollback**
- Gate v2 output behind flag and default callers back to v1 shape.

### Task: B2 — Deterministic budget builder

**Objective**
- Deterministic segment ranking/inclusion with explicit exclusion reasons under strict token/character budget.

**Pre-flight checks**
- [x] Confirm model budget assumptions in product/spec docs.
- [x] Validate current context inputs needed for ranking.

**Safety constraints**
- [x] Approval gate preserved.
- [x] Runner has no GitHub write token access.
- [x] Deterministic ordering/hash behavior maintained.
- [x] Idempotent retry behavior preserved or improved.

**Implementation steps**
1. Define deterministic ranking tuple for segments.
2. Add budget accounting ledger in manifest output.
3. Record exclusions with machine-readable reason codes.

**Likely files touched**
- `pm_bot/server/context_pack.py`
- `docs/contracts/context_pack.md`
- `tests/test_v2_context_pack.py`

**Tests**
- Unit: tie-breaking order and exclusion reason determinism.
- Integration: budget never exceeded for fixture corpus.
- HTTP/UI: API response includes inclusion/exclusion summaries.

**Acceptance criteria**
- Budget policy is deterministic and auditable with complete exclusion evidence.

**Rollback**
- Revert to simple truncation mode while retaining existing hash envelope.

### Task: B3 — Redaction + provenance manifesting

**Objective**
- Add structured redaction markers with provenance to prevent secrets leakage while preserving auditability.

**Pre-flight checks**
- [x] Confirm sensitive-field patterns from existing contracts/spec docs.
- [x] Validate no plaintext secret persistence in DB audit trail.

**Safety constraints**
- [x] Approval gate preserved.
- [x] Runner has no GitHub write token access.
- [x] Deterministic ordering/hash behavior maintained.
- [x] Idempotent retry behavior preserved or improved.

**Implementation steps**
1. Add redaction detector/normalizer for known secret classes.
2. Persist redaction counts/categories (not values) in context manifest.
3. Add provenance entries linking redactions to source segment IDs.

**Likely files touched**
- `pm_bot/server/context_pack.py`
- `docs/contracts/context_pack.md`
- `tests/test_v2_context_pack.py`

**Tests**
- Unit: secret-shaped inputs are redacted deterministically.
- Integration: manifest exposes counts/categories only.
- HTTP/UI: no redacted values appear in response payload snapshots.

**Acceptance criteria**
- Manifest reports redaction evidence without leaking sensitive data.

**Rollback**
- Disable redaction metadata expansion and retain prior sanitized content path.

### Task: B4 — Context ledger + audit chain

**Objective**
- Link context pack budget/hash artifacts into audit events and run-level traceability.

**Pre-flight checks**
- [x] Verify existing audit append surfaces in app/reporting paths.
- [x] Confirm run-id correlation conventions.

**Safety constraints**
- [x] Approval gate preserved.
- [x] Runner has no GitHub write token access.
- [x] Deterministic ordering/hash behavior maintained.
- [x] Idempotent retry behavior preserved or improved.

**Implementation steps**
1. Add context_pack_built audit event shape with hash/budget summary.
2. Associate event with run IDs and requesting actor.
3. Expose audit lookup filters for context events.

**Likely files touched**
- `pm_bot/server/app.py`
- `pm_bot/server/db.py`
- `docs/contracts/agent_run_spec.md`
- `tests/test_reporting.py`

**Tests**
- Unit: audit event schema and persistence validation.
- Integration: run-level event chains include context pack events.
- HTTP/UI: reporting endpoint renders context-pack linkage.

**Acceptance criteria**
- Context builds are fully traceable by hash and run in audit records.

**Rollback**
- Stop emitting new context events while preserving existing audit paths.

### Task: C1 — Runner state machine lifecycle ✅

**Objective**
- Extend runner state transitions with strict transition validation and terminal-state invariants.

**Pre-flight checks**
- [x] Review changeset approval lifecycle and current statuses.
- [x] Confirm ADR expectations for approval-gated execution.

**Safety constraints**
- [x] Approval gate preserved.
- [x] Runner has no GitHub write token access.
- [x] Deterministic ordering/hash behavior maintained.
- [x] Idempotent retry behavior preserved or improved.

**Implementation steps**
1. Define normalized run statuses and allowed transitions.
2. Persist transition timestamps/reason metadata.
3. Reject invalid transition attempts with deterministic reason codes.

**Likely files touched**
- `pm_bot/server/db.py`
- `pm_bot/server/changesets.py`
- `docs/contracts/agent_run_spec.md`
- `tests/test_v1_server.py`

**Tests**
- Unit: transition matrix coverage.
- Integration: invalid transitions are denied and audited.
- HTTP/UI: status reads reflect terminal states consistently.

**Acceptance criteria**
- Run lifecycle is explicit, enforceable, and audited.

**Rollback**
- Keep status fields but bypass strict transition validation.

### Task: C2 — Local queue/worker semantics ✅

**Objective**
- Implement bounded-concurrency queue claiming with retry/dead-letter semantics and idempotent claim behavior.

**Pre-flight checks**
- [x] Confirm existing retry/idempotency logic and dead-letter handling.
- [x] Validate local-only worker assumptions in ops docs.

**Safety constraints**
- [x] Approval gate preserved.
- [x] Runner has no GitHub write token access.
- [x] Deterministic ordering/hash behavior maintained.
- [x] Idempotent retry behavior preserved or improved.

**Implementation steps**
1. Add claim lease fields and bounded worker selection query.
2. Enforce retry budgets with backoff metadata.
3. Move exhausted jobs to dead-letter state with reason summaries.

**Likely files touched**
- `pm_bot/server/db.py`
- `pm_bot/server/changesets.py`
- `docs/spec/product.md`
- `tests/test_reliability_v4.py`

**Tests**
- Unit: idempotent claim behavior under duplicate worker polling.
- Integration: retries/dead-letter flow across transient failures.
- HTTP/UI: pending views exclude leased/exhausted jobs appropriately.

**Acceptance criteria**
- Queue execution is bounded, idempotent, and deterministic under retries.

**Rollback**
- Disable worker claiming mode and return to synchronous/manual execution path.

### Task: C3 — Runner adapter contract (manual first) ✅

**Objective**
- Introduce portable runner adapter interface (`submit/poll/fetch_artifacts/cancel`) with manual adapter baseline.

**Pre-flight checks**
- [x] Confirm no adapter path can bypass approval checks.
- [x] Verify artifact storage/read constraints in local mode.

**Safety constraints**
- [x] Approval gate preserved.
- [x] Runner has no GitHub write token access.
- [x] Deterministic ordering/hash behavior maintained.
- [x] Idempotent retry behavior preserved or improved.

**Implementation steps**
1. Define adapter protocol/ABC and response contracts.
2. Implement manual/local adapter and wiring through run lifecycle.
3. Add adapter selection config with safe defaults.

**Likely files touched**
- `pm_bot/server/runner.py`
- `pm_bot/server/app.py`
- `docs/contracts/agent_run_spec.md`
- `tests/test_runner_adapter.py`

**Tests**
- Unit: contract conformance tests for manual adapter.
- Integration: approve→execute path uses adapter and records artifacts.
- HTTP/UI: run status reflects adapter job state transitions.

**Acceptance criteria**
- Local adapter provides end-to-end portable execution baseline with approval gating.

**Rollback**
- Keep interface docs but route execution through pre-adapter path.

### Task: C4 — Additional runner adapters (optional) ✅

**Objective**
- Add provider-specific adapters only after C1–C3 stability criteria hold.

**Pre-flight checks**
- [x] Confirm C1–C3 acceptance metrics are green.
- [x] Confirm provider credentials and network boundaries are policy-approved for local stub adapter rollout.

**Safety constraints**
- [x] Approval gate preserved.
- [x] Runner has no GitHub write token access.
- [x] Deterministic ordering/hash behavior maintained.
- [x] Idempotent retry behavior preserved or improved.

**Implementation steps**
1. [x] Implement provider adapter behind feature flag.
2. [x] Reuse adapter conformance suite from C3.
3. [x] Add provider-specific failure mapping to common reason codes.

**Likely files touched**
- `pm_bot/server/runner_adapters/*.py`
- `docs/spec/product.md`
- `tests/test_runner_adapter.py`

**Tests**
- Unit: adapter contract parity against manual adapter.
- Integration: provider failure paths map to deterministic states.
- HTTP/UI: status surfaces adapter name + normalized failure reason.

**Acceptance criteria**
- Optional adapters are contract-compatible and policy-safe.

**Rollback**
- Disable provider adapter flag and fall back to manual adapter.

### Task: D1 — Unified inbox schema + aggregator ✅

**Objective**
- Create unified inbox item schema and backend aggregator joining pm-bot approvals with GitHub triage/review items.

**Pre-flight checks**
- [x] Link repo inventory section 7 for current inbox/tree UI.
- [x] Confirm GitHub connector read APIs required for external feed aggregation.

**Safety constraints**
- [x] Approval gate preserved.
- [x] Runner has no GitHub write token access.
- [x] Deterministic ordering/hash behavior maintained.
- [x] Idempotent retry behavior preserved or improved.

**Implementation steps**
1. Define normalized inbox item schema with `source` discriminator.
2. Implement aggregator endpoint combining internal pending approvals and external GitHub items.
3. Add deterministic merge/sort rules and staleness metadata.

**Likely files touched**
- `pm_bot/server/app.py`
- `pm_bot/server/github_connector.py`
- `docs/spec/inbox.md`
- `tests/test_server_http_contract.py`

**Tests**
- Unit: source normalization and stable merge order.
- Integration: aggregator includes both internal and external items.
- HTTP/UI: unified endpoint contract snapshots.

**Acceptance criteria**
- Unified inbox endpoint returns clearly typed, deterministic mixed-source items.

**Rollback**
- Revert to pm-bot-only pending approval inbox endpoint.

### Task: D2 — Search-safe query/caching strategy ✅

**Objective**
- Add bounded GitHub query decomposition plus cache controls to avoid rate-limit churn.

**Pre-flight checks**
- [x] Confirm auth/rate-limit guidance from GitHub docs.
- [x] Validate current cache/TTL helpers (if any) for reuse.

**Safety constraints**
- [x] Approval gate preserved.
- [x] Runner has no GitHub write token access.
- [x] Deterministic ordering/hash behavior maintained.
- [x] Idempotent retry behavior preserved or improved.

**Implementation steps**
1. Implement query chunking strategy for operator/length constraints.
2. Add bounded TTL cache keyed by normalized query signature.
3. Emit cache hit/miss + rate-limit telemetry in diagnostics output.

**Likely files touched**
- `pm_bot/server/github_connector_api.py`
- `pm_bot/server/app.py`
- `docs/github/auth-and-tokens.md`
- `tests/test_github_connector_api.py`

**Tests**
- Unit: query normalizer and cache key determinism.
- Integration: repeated inbox fetches honor TTL and call budget caps.
- HTTP/UI: diagnostics payload includes cache/rate-limit fields.

**Acceptance criteria**
- Inbox aggregation remains responsive while keeping search calls bounded/cached.

**Rollback**
- Disable external query path and continue serving internal-only inbox feed.

### Task: D3 — Inbox UI expansion with audit panel ✅

**Objective**
- Expand UI inbox with tabs, filters, and audit details while keeping approval actions scoped to pm-bot-native items.

**Pre-flight checks**
- [x] Confirm current React route/page architecture in `ui/src/`.
- [x] Validate accessibility and interaction expectations from existing components.

**Safety constraints**
- [x] Approval gate preserved.
- [x] Runner has no GitHub write token access.
- [x] Deterministic ordering/hash behavior maintained.
- [x] Idempotent retry behavior preserved or improved.

**Implementation steps**
1. Add source tabs and filter controls to inbox page.
2. Add audit detail panel for pm-bot approval items.
3. Render external GitHub items as outbound links with no internal approve controls.

**Likely files touched**
- `ui/src/pages/InboxPage.tsx`
- `ui/src/components/*`
- `ui/src/api.ts`
- `tests/ui/*`

**Tests**
- Unit: filter/tabs state behavior and item grouping.
- Integration: approval button availability gated by item `source`.
- HTTP/UI: visual smoke + API contract checks for new inbox payload shape.

**Acceptance criteria**
- Operators can triage unified items while only executing audited approvals for internal changesets.

**Rollback**
- Switch UI back to existing pending approvals list rendering.
