# Agent Roadmap v6 — Natural-Text Multi-Repo Planning + GUI Agent Operations + Multi-Agent Audit
_Date: 2026-02-25_

## Purpose

This roadmap turns the M0–M3 execution plan into a repo-native v6 stage focused on three operator-visible outcomes:

1. Natural text → LLM-assisted ReportIR draft → multi-repo changeset preview → human-gated approval in GUI.
2. GUI-driven agent deployment using deterministic context packs.
3. Audit-grade visibility for multi-agent orchestration.

This v6 plan is intentionally additive and preserves existing safety/determinism invariants.

> **Implementation status note (2026-02-26):** Plan Intake GUI route and guided intake/confirm/preview/propose interactions are shipped and route-tested. Full closure remains contingent on explicit end-to-end GUI evidence that links Plan Intake proposal output to Inbox approval/apply outcomes.

---

## Stage boundary

### In scope
- GUI/operator workflows that compose existing backend capabilities into complete end-to-end flows.
- LLM-assisted intake path that converts natural text into editable `report_ir/v1` drafts.
- Deterministic ReportIR → changeset proposal mapping for multi-repo operations.
- Context-pack and agent-run controls from GUI (proposal/approval/execution visibility).
- Multi-agent audit views and report rollups keyed by `run_id`.

### Out of scope
- Full SaaS control plane, billing, or tenant-isolation commercialization.
- Bypasses to approval gates or direct agent write privileges.
- New non-GitHub mutation connectors.

### Dependencies
- Existing approval-gated changeset engine and policy-denial reason codes.
- Existing `context_pack/v2` hash/budget/redaction semantics.
- Existing `agent_run_spec/v1` lifecycle and runner adapter contract.
- Existing unified inbox and tree UI baseline.

### Exit criteria
- A user can paste natural text, review/edit generated ReportIR, preview multi-repo writes, and approve from GUI.
- A user can create/approve/execute agent runs from GUI with explicit context-pack binding.
- Operators can audit run chains across context, agent, changeset, webhook, and reporting events.

### Owner type
- Mixed (agent implementation with human approvals on policy/risk boundaries and rollout decisions).

---

## Current baseline (do not re-implement)

Already present in repo and treated as baseline capabilities:

1. Approval-gated changesets and guardrailed write policies.
2. Deterministic context packs (`context_pack/v2`) with hash/budget/redaction metadata.
3. Agent-run API surfaces and local/manual adapter lifecycle.
4. Unified inbox and tree/dependency UI MVP.
5. Weekly reporting and audit event storage primitives.

v6 should therefore be executed as orchestration/UX composition + audit hardening, not a net-new platform reset.

---

## Execution tracks (maps to M0–M3)

## Track A — M0 GUI orchestration baseline (first shippable)

### Objective
Expose existing agent/context operations through operator-grade GUI surfaces without changing core safety semantics.

### Build on
- `ui/src/App.tsx`, `ui/src/InboxPage.tsx`, `ui/src/api.ts`
- `pm_bot/server/app.py`
- `docs/contracts/context_pack.md`
- `docs/contracts/agent_run_spec.md`

### Phases
1. **A1: GUI route expansion**
   - Add Agent Runs route and Context Pack route to app shell.
   - Keep deterministic route-state and predictable defaults.
2. **A2: API client coverage**
   - Add typed API bindings for `/context-pack` and `/agent-runs/*`.
   - Surface normalized error/reason-code rendering in UI.
3. **A3: Approval-preserving actions**
   - Ensure run creation is proposed by default.
   - Ensure execution UI is disabled until approved state is present.

### Exit criteria
- Operator can create and inspect a proposed run in UI.
- Operator can request/build a context pack by issue ref and see hash/budget manifest.
- No UI action bypasses the backend approval lifecycle.

---

## Track B — M1 natural-text to multi-repo changeset preview

### Objective
Deliver safe, deterministic paragraph-to-plan workflow with explicit human editing and approval checkpoints.

### Build on
- `docs/contracts/report_ir_v1.md`
- `docs/contracts/changesets.md`
- `docs/spec/product.md`
- `pm_bot/server/app.py`

### Phases
1. **B1: Intake contract and endpoint**
   - Add endpoint for natural-text intake request + metadata.
   - Persist request/response audit envelope with run correlation.
2. **B2: LLM-assisted ReportIR draft generation**
   - Generate `report_ir/v1` draft from natural text.
   - Emit deterministic validation errors and triage hints when required fields are missing.
3. **B3: Human edit/confirm checkpoint**
   - Add explicit review/confirm step before any changeset proposal.
   - Preserve raw draft plus edited version for audit traceability.
4. **B4: ReportIR → multi-repo changeset preview**
   - Deterministically map confirmed ReportIR to changeset proposals.
   - Show grouped preview by repo + operation + target references.
5. **B5: Approval handoff to existing engine**
   - Route accepted preview into standard propose/approve/apply pipeline.
   - Reuse idempotency keys for replay-safe behavior.

### Exit criteria
- Natural-text input produces an editable ReportIR draft.
- Confirmed ReportIR yields deterministic multi-repo proposal preview.
- Repeated confirmations do not duplicate writes (idempotent convergence).

---

## Track C — M2 GUI agent deployment with context binding

### Objective
Complete end-to-end GUI operator flow for context-backed agent runs with clear lifecycle and artifact visibility.

### Build on
- `pm_bot/server/runner.py`
- `pm_bot/server/app.py`
- `docs/contracts/agent_run_spec.md`
- `docs/contracts/context_pack.md`

### Phases
1. **C1: Run-spec form + validation**
   - Build UI form for `run_id`, `intent`, model/budget, tools/outputs allowed, and adapter selection.
   - Perform deterministic pre-submit validation aligned to contract-required fields.
2. **C2: Context-pack binding UX**
   - Build/select context pack in-flow and attach hash/version to proposed run.
   - Display budget usage and exclusion/redaction summary before submit.
3. **C3: Lifecycle operations panel**
   - Render status transitions (`proposed → approved → running → completed/failed/cancelled`).
   - Provide guarded transition actions with actor/reason capture.
4. **C4: Artifact/result visibility**
   - Display adapter job IDs, artifact paths, terminal reason codes, retry/dead-letter outcomes.
   - Add deterministic empty-state handling for runs without artifacts.

### Exit criteria
- Operators can execute full run lifecycle from GUI without shell intervention.
- Run context binding is explicit (hash/version visible).
- Failures are diagnosable from UI with reason codes and retry state.

---

## Track D — M3 multi-agent audit and operations visibility

### Objective
Provide operator-grade traceability and rollups for concurrent/multi-agent orchestration.

### Build on
- `pm_bot/server/db.py` audit primitives
- `pm_bot/server/reporting.py`
- `docs/spec/reporting.md`
- `docs/spec/inbox.md`

### Phases
1. **D1: Audit chain query surface**
   - Add API filters by `run_id`, `event_type`, actor, repo, and time window.
   - Return deterministic ordering and pagination semantics.
2. **D2: Correlated chain visualization**
   - UI timeline linking context-pack, run transitions, changesets, webhooks, and report generation events.
   - Highlight missing links and partial chains as warnings.
3. **D3: Multi-agent rollups and risk signals**
   - Add metrics for completion rate, retry/dead-letter, denial distributions, queue age.
   - Include top failing reason codes and repo concentration summaries.
4. **D4: Operations playbook hooks**
   - Link surfaced anomalies to runbook actions (retry storms, denial spikes, webhook drift).
   - Add exportable incident bundles for human review.

### Exit criteria
- Any run can be traced end-to-end from proposal through final outputs.
- Weekly reporting includes multi-agent orchestration sections with sample sizes.
- Operators can triage incidents without querying raw DB tables.

---

## Cross-track safety and compatibility requirements

All v6 tasks MUST satisfy the following:

- Approval gate preserved for writes and token-spend operations.
- Runner contexts remain isolated from privileged GitHub write credentials.
- Deterministic ordering/hash semantics maintained for context and graph-related outputs.
- Idempotent retry/dead-letter behavior preserved or improved.
- Projects heading compatibility remains unchanged (`Area`, `Priority`, `Size`, `Estimate (hrs)`, `Risk`, `Blocked by`, `Actual (hrs)`).

---

## KPIs (v6)

- **Intake determinism:** identical confirmed ReportIR inputs yield byte-stable proposal previews.
- **Human-gated safety:** 100% of applied writes and executed agent runs have prior approval records.
- **GUI operability:** ≥95% of normal operator actions (build context, propose run, approve, execute, inspect) can be completed without CLI fallback.
- **Audit completeness:** ≥99% of run chains contain linked context, run transition, and outcome events.

---

## Rollout and rollback

### Rollout
- Release per-track in small slices; each phase independently releasable.
- Feature-flag new natural-text intake and advanced audit surfaces.
- Keep API and UI contract fixtures updated in the same PR.

### Rollback
- Disable v6 intake/GUI features via flags while retaining existing v0–v5 paths.
- Revert additive UI routes first, then backend intake/audit extensions if required.
- Preserve audit append-only behavior during rollback.

---

## Task-card template (v6 execution slices)

Use this template for each v6 PR.

```markdown
### Task: <track-phase short name>

**Objective**
- ...

**Pre-flight checks**
- [ ] Link to `docs/implementation/repo-inventory.md` module/file sections
- [ ] Confirm current API contract tests and UI test coverage locations
- [ ] Confirm status/reporting fields impacted by this slice

**Safety constraints**
- [ ] Approval gate preserved
- [ ] No privileged GitHub write token exposure in runner/execution surfaces
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
- Integration:
- HTTP/UI:

**Acceptance criteria**
- ...

**Rollback**
- ...
```

---

## Suggested phase order (smallest risk first)

1. Track A (A1–A3)
2. Track B (B1–B5)
3. Track C (C1–C4)
4. Track D (D1–D4)

Parallelization guidance:
- B2 and C1 can run in parallel once A2 API contract changes are stable.
- D2 should wait for stable event/query schemas from D1.

