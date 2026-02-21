# Agent Roadmap v3 — SaaS Shape (Implement Later)
_Date: 2026-02-21_

## Mission (shape only)
Turn the personal tool into a product without rewriting core logic.

### Deliverables
- Multi-tenant auth + tenant isolation
- GitHub App installation per org, repo allowlists per tenant
- Policy engine (role-based approvals, write scopes)
- Vector retrieval (ADR/docs/issues) for better context packs
- Advanced estimator (hierarchical/Bayesian) + model versioning
- Billing + token metering

### Architecture notes
- Keep canonical WorkItem schema stable; add versioning.
- Make connectors pluggable (GitHub now, others later).
- Audit log must be immutable per tenant.

### Success criteria
- A new org can onboard via GitHub App install + minimal config.
- No cross-tenant data leakage.
- Agents remain draft-only by default, with auditable approvals.
