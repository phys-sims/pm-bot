# Future Roadmap — Long-horizon SaaS Shape (Non-Executable Now)
_Date: 2026-02-21_

> [!WARNING]
> **Long-horizon / non-executable now.**
> **Not the default roadmap for current implementation sequencing.**
> Use `docs/roadmaps/agent-roadmap-v3-near-term.md` (and successive near-term stages) for active execution planning.

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
