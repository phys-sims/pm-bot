# Agent Roadmap v5 Org Readiness — Multi-tenant Prerequisites Without Full SaaS Billing
_Date: 2026-02-22_

## Stage boundary
### In scope
- Tenant-aware data model preparation (namespacing keys, ownership metadata, isolation checks).
- Auth boundary prep for org-level onboarding controls.
- Installation/onboarding flow scaffolding (without monetization complexity).
- Compliance/audit posture upgrades for org trust readiness.

### Out of scope
- Full SaaS billing, invoicing, or subscription lifecycle.
- Production-grade multi-tenant control plane.
- Marketplace commercialization.

### Dependencies
- v4 reliability baseline and policy hardening.
- ADRs for auth/safety/contracts/ops architecture decisions.
- Existing audit and approval trails as extension points.

### Exit criteria
- Data model includes tenant-aware primitives without breaking single-tenant compatibility.
- Auth boundaries are explicit for org/install context.
- Onboarding/runbooks and audit controls meet defined readiness checklist.

### Owner type
- Mixed (agent builds scaffolding; human decisions required for compliance/legal/policy approvals).

## Mission
Prepare the product for safe organization onboarding by introducing tenant-aware and compliance-oriented foundations while keeping operational complexity bounded.

## Codex-sized implementation slices (1–2 days each)
1. **Tenant-aware schema prep**
   - Add optional tenant/org identifiers in core records.
   - Add compatibility tests ensuring single-tenant default behavior remains intact.
2. **Auth boundary scaffolding**
   - Define install/org context boundaries and required claims.
   - Add denial paths for missing/invalid org context.
3. **Onboarding flow skeleton**
   - Create setup checklist and state machine for installation readiness.
   - Add dry-run onboarding validation command/API.
4. **Compliance and audit uplift**
   - Expand audit event taxonomy for org-sensitive operations.
   - Add retention/export guidance and verification checks.

## KPIs
- 100% of write/audit records include tenant context or explicit single-tenant default marker.
- Onboarding dry-run success rate and failure reason distribution are measurable.
- Compliance checklist coverage tracked in status reporting.

## Required checks
- `pytest -q`
- `ruff check .`
- `ruff format .`
- targeted auth/audit/onboarding validation tests

## Rollout and rollback
- Rollout with tenant-awareness feature toggles default-off.
- Rollback by toggling off tenant-aware paths and reverting non-schema-breaking scaffolding commits.

## Acceptance criteria
- Org-readiness prerequisites are implemented and measurable.
- No regression in existing single-tenant workflows.
- Docs/spec/contracts/status capture tenant-prep boundaries clearly.

## Execution companion
- Use `docs/implementation/repo-inventory.md` as the current-state source before opening N3/v5 PR slices.
- Use `docs/roadmaps/org-scale-roadmap-reconciliation.md` to decompose the larger org-scale M0–M5 plan into repo-native Tracks A–D (graph, context packs, runner portability, unified inbox).
- Keep this v5 document as the stage boundary and acceptance gate; track-level sequencing lives in the reconciliation roadmap.
