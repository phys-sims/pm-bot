# Web UI Action Plan (MVP)
_Date: 2026-02-23_

## Goal
Deliver a minimal, production-shaped web UI for pm-bot that enables:
1) approval inbox workflows,
2) tree/dependency visualization,
3) safe, auditable changeset actions.

This plan assumes current server-layer capabilities already exist and focuses on closing the remaining API + frontend gaps.

## Scope and non-goals

### In scope (MVP)
- HTTP endpoints required by an initial UI shell.
- A small SPA (read-heavy + approval actions).
- End-to-end tests for 2-3 critical journeys.
- Documentation/runbook updates for local startup and validation.

### Out of scope (MVP)
- Multi-tenant auth/billing.
- Full dashboard/report builder.
- Broad design system effort.

## Milestones

### M1 — API surface for UI (2-3 days)
**Deliverables**
- Add HTTP routes for:
  - `GET /changesets/pending`
  - `POST /changesets/{id}/approve`
  - `GET /graph/tree`
  - `GET /graph/deps`
  - `GET /estimator/snapshot`
  - `GET /reports/weekly/latest` (or latest known report metadata)
- Ensure responses are deterministic and aligned with contract/spec docs.
- Return policy reason codes and clear validation errors for denied actions.

**Acceptance criteria**
- Existing tests remain green.
- New HTTP contract tests cover status code + schema shape for each route.
- Approval gate remains non-bypassable via HTTP.

### M2 — Frontend skeleton + Approval Inbox (2-3 days)
**Deliverables**
- Create `ui/` app shell (React + Vite or equivalent lightweight SPA).
- Implement Inbox page:
  - list pending changesets
  - show operation/repo/summary
  - approve action with confirmation
  - success/error toasts with reason codes
- Add local config to point at `pm_bot.server.app:app`.

**Acceptance criteria**
- A user can approve a pending changeset from the UI.
- Audit event appears after approval/apply flow.
- No direct write action bypasses proposal/approval flow.

### M3 — Tree + dependency view (2-3 days)
**Deliverables**
- Tree page consuming `GET /graph/tree`.
- Dependency overlay consuming `GET /graph/deps`.
- Provenance badges (`sub_issue`, `dependency`, `checklist`).
- Warning panel for cycles/conflicts/unresolved references.

**Acceptance criteria**
- UI displays graph warnings surfaced by API.
- Source provenance is visible for all rendered edges.
- Empty/sparse/error states are handled deterministically.

### M4 — Quality gates + docs + release checklist (1-2 days)
**Deliverables**
- Frontend unit tests for critical components.
- Playwright e2e for top user journeys:
  1) open inbox and approve a changeset,
  2) open tree for root item and inspect provenance,
  3) error path for denied approval/invalid request.
- Update README with UI startup instructions.
- Update runbook for local demo flow.

**Acceptance criteria**
- CI includes frontend lint/test and e2e gate for critical journeys.
- Docs are sufficient for a clean-environment local demo.

## Work breakdown by track

### Backend track
- Implement UI-needed HTTP routes around existing service methods.
- Add response models (or stable JSON schemas) for route outputs.
- Harden error mapping to stable reason codes.

### Frontend track
- Build app shell and route layout (`/inbox`, `/tree`).
- Create typed API client module.
- Implement accessible controls and keyboard-friendly interactions.

### QA track
- Add HTTP contract tests.
- Add frontend component tests.
- Add Playwright smoke/e2e journeys.

### Docs/ops track
- Add UI local run commands to README.
- Add troubleshooting section (API unavailable, CORS/config mismatch).
- Update STATUS.md for progress snapshots per milestone completion.

## Risks and mitigations
- **Risk:** API/contract drift between backend and SPA.
  - **Mitigation:** schema/contract fixtures + contract tests in CI.
- **Risk:** Approval flow regression bypassing safety gates.
  - **Mitigation:** explicit denied-without-approval tests at HTTP and e2e levels.
- **Risk:** UI complexity creep.
  - **Mitigation:** keep MVP to inbox + tree/deps only.

## Suggested execution sequence (10 working days)
- Day 1-3: M1 API routes + tests.
- Day 4-6: M2 inbox UI + tests.
- Day 7-8: M3 tree/deps UI + tests.
- Day 9-10: M4 e2e/docs/release gate.

## Definition of done for this plan
- Local demo starts with one backend command and one UI command.
- User can perform one full safe workflow: propose -> approve -> verify audit.
- User can view one root tree with provenance and warnings.
- CI enforces tests for both backend HTTP contract and frontend critical journeys.
