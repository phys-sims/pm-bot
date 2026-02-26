# Org-scale roadmap reconciliation (repo-aligned)
_Date: 2026-02-25_

## Purpose

This plan decomposes the provided org-scale M0–M5 roadmap into repository-appropriate execution tracks that build on:

- existing v0–v4 deliverables,
- active N3/v5 positioning,
- existing contracts/specs/ADRs already present in this repo.

It is intentionally additive and local-first, aligned with approval-gated write safety.

---

## Current baseline (from repo docs)

Already implemented and should be treated as baseline, not rework:

1. Approval-gated changeset writes + deterministic reason-coded denials.
2. Local-first service + SQLite control-plane storage.
3. Workgraph/tree/dependency APIs with provenance handling.
4. Context pack and AgentRunSpec contract surface (v1-level) present.
5. UI MVP for inbox and tree views exists.

This means the large roadmap should be parsed as **incremental hardening and expansion**, not as a full net-new architecture bootstrap.

---

## Parsed roadmap structure for this repo

Use four repo-specific tracks that map directly to existing docs and stage boundaries.

## Track A — Cross-repo WorkGraph hardening (maps mostly to M1)

### Objective
Promote current graph implementation to org-aware, typed-edge, cross-repo identity semantics without breaking existing endpoints.

### Build on
- `docs/contracts/workgraph.md`
- `docs/github/tree-and-dependencies.md`
- `docs/spec/graph-api.md`
- ADR-0004 (tree edge priority)

### Phases
1. **A1: Data model extensions (additive)**
   - Add org/repo/stable-id oriented graph tables or compatibility views.
   - Preserve current read paths during migration.
2. **A2: Ingestion expansion**
   - Add GitHub sub-issue and dependency endpoint ingestion via connector wrapper.
   - Record typed edge provenance and ingestion diagnostics snapshots.
3. **A3: Deterministic reconciliation**
   - Stable ordering and cycle warnings at API boundary.
   - Partial-ingestion status with explicit warnings/reason codes.

### Exit criteria
- `GET /graph/tree` and dependency views are stable for same DB state.
- Cross-repo identities resolve via stable GitHub node IDs.
- Snapshot diagnostics include counts, warnings, and call budget usage.

---

## Track B — Context Pack v2 + auditability upgrades (maps mostly to M2)

### Objective
Upgrade existing context pack behavior to deterministic/auditable v2 manifests with budget governance and redaction evidence.

### Build on
- `docs/contracts/context_pack.md`
- `docs/contracts/agent_run_spec.md`
- `docs/spec/product.md`
- ADR-0002 (contract-first schemas)

### Phases
1. **B1: Contract + schema version bump**
   - Add `context_pack/v2` schema and canonical serialization/hash rules.
2. **B2: Deterministic token-budget builder**
   - Deterministic segment ranking/inclusion and explicit exclusions.
3. **B3: Redaction + provenance**
   - Structured secret redaction with manifest summaries.
4. **B4: Ledger + audit chain integration**
   - Record budget/estimate entries and hash-linked audit events.

### Exit criteria
- Same inputs always produce the same pack hash.
- Token budget is never exceeded.
- Manifest explains redactions/exclusions without leaking sensitive values.

---

## Track C — Runner control-plane portability (maps mostly to M3)

### Objective
Formalize portable runner execution while preserving existing approval boundaries and no-token-leak posture.

### Build on
- `docs/contracts/agent_run_spec.md`
- `docs/contracts/changesets.md`
- `docs/github/auth-and-tokens.md`
- ADR-0001, ADR-0005, ADR-0006

### Phases
1. **C1: Agent run state machine + DB lifecycle**
   - Expand run statuses and transition validation.
2. **C2: Local queue/worker semantics**
   - Bounded concurrency, retry, dead-letter, idempotent claiming.
3. **C3: Adapter interface + manual runner first**
   - `submit/poll/fetch_artifacts/cancel` contract.
4. **C4 (optional): additional adapters**
   - Add provider-specific adapter(s) after manual baseline is stable.

### Exit criteria
- Propose → approve → execute path works end-to-end in local mode.
- Runner execution cannot proceed without approval record.
- Runner contexts never include write-scoped GitHub credentials.

---

## Track D — Unified inbox and org triage (maps mostly to M4)

### Objective
Evolve current inbox MVP into an aggregated operator surface across pm-bot approvals + GitHub review/triage streams.

### Build on
- `docs/spec/inbox.md`
- existing UI inbox/tree implementation in `ui/`
- GitHub auth/rate-limit guidance in `docs/github/auth-and-tokens.md`

### Phases
1. **D1: Inbox item schema + backend aggregator**
   - Merge pm-bot pending approvals with GitHub search-backed items.
2. **D2: Search-safe query strategy + cache**
   - Query decomposition to fit operator/length/rate constraints.
3. **D3: UI expansion**
   - Tabs/filters/audit panel; approval actions only for pm-bot-native objects.

### Exit criteria
- Inbox calls are cached and bounded to avoid search-rate limit churn.
- UI clearly separates internal approvals from external GitHub links.
- Approval actions remain gate-checked and audited.

---

## How this maps to existing roadmap files

- Keep `agent-roadmap-v5-org-readiness.md` as the stage boundary narrative.
- Use this document as the **execution decomposition** for the org-scale gaps.
- Future work beyond these tracks (auth app rollout, retention exports, SLO hardening) remains under M5/v5 hardening and can be appended after tracks A–D ship.

---

## Task-card template for repo execution

Use this task card format for each PR slice in Tracks A–D.

```markdown
### Task: <track-phase short name>

**Objective**
- ...

**Pre-flight checks**
- [ ] Link to `docs/implementation/repo-inventory.md` section for modules/files
- [ ] Confirm current DB/config/logging/test patterns

**Safety constraints**
- [ ] Approval gate preserved
- [ ] Runner has no GitHub write token access
- [ ] Deterministic ordering/hash behavior maintained
- [ ] Idempotent retry behavior preserved or improved

**Implementation steps**
1. ...
2. ...
3. ...

**Likely files touched**
- ...

**Tests**
- Unit:
  - ...
- Integration:
  - ...
- HTTP/UI:
  - ...

**Acceptance criteria**
- ...

**Rollback**
- ...
```

---

## Sequencing recommendation

1. Track A (graph hardening) and Track B (context pack v2) first, because they are prerequisites for safe runner portability.
2. Track C next to standardize run execution around approved specs.
3. Track D in parallel late-stage once search/cache strategy is clear.
4. M5 hardening (GitHub App auth, retention exports, SLO runbooks) after A–D baseline acceptance.

---

## Implemented execution plan cards (all track phases)

The execution cards were moved to a dedicated agent-editable file to keep this reconciliation document stable as the source of truth.

- Editable execution cards: `docs/roadmaps/org-scale-execution-task-cards.md`
- Rule: update task progress/cards in the execution file, and only update this reconciliation doc when Track definitions or source-of-truth mapping changes.
