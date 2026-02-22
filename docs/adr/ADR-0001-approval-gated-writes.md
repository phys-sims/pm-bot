# Approval-gated writes via ChangesetBundle

- **ADR ID:** ADR-0001
- **Status:** Proposed
- **Date:** 2026-02-22
- **Deciders:** @you
- **Area:** server
- **Related:** `pm_bot/server/changesets.py`, `pm_bot/server/github_connector.py`, `pm_bot/server/db.py`
- **Tags:** safety, approvals, changesets, audit, github
- **Scope:** repo
- **Visibility:** public

## Context

pm-bot is intended to interact with privileged external systems (GitHub Issues, Projects, and potentially PRs). These operations have:

- **risk** (writing to the wrong repo, corrupting issue bodies, breaking Projects sync)
- **cost** (agent token spend, large batch operations)
- **operational blast radius** (a bad run can create dozens of artifacts)

Therefore, pm-bot must be safe-by-default and auditable.

Additionally, GitHub Project field sync depends on deterministic headings, so “write correctness” is sensitive to formatting.

## Options considered

### Option A — Direct writes (agent or tool writes immediately)

- **Description:** when pm-bot decides something should be created/updated, it performs the GitHub mutation immediately.
- **Pros:**
  - simple implementation
  - fast to “see results”
- **Cons:**
  - unsafe (accidental writes)
  - difficult to audit intent vs outcome
  - hard to recover from partial failures
  - encourages “guessing” instead of review
- **Risks / Unknowns:**
  - severe blast radius if parsing/rendering drifts
  - increased likelihood of token runaway if agents are integrated
- **Security / privacy:**
  - requires privileged tokens in more code paths
- **Testing impact:**
  - requires very strong integration tests to be trustworthy

### Option B — Propose → approve → apply changesets (ChangesetBundle)

- **Description:** pm-bot computes proposed changes (changesets), shows a preview diff, then requires a recorded approval before applying mutations.
- **Pros:**
  - hard safety gate (no accidental writes)
  - excellent auditability (intent and approval are explicit)
  - easier to make idempotent (stable idempotency keys)
  - reviewable diffs reduce “silent drift”
- **Cons:**
  - requires an approval UX (CLI or UI)
  - adds state management (bundle status, approvals, execution logs)
- **Risks / Unknowns:**
  - approval UX must be “cheap” or it becomes friction
- **Operational impact:**
  - cleaner incident recovery: you can see exactly what was applied
- **Security / privacy:**
  - privileged tokens can be isolated to the apply step
- **Testing impact:**
  - enables deterministic unit tests for “bundle generation”
  - integration tests focus on connector correctness

## Decision

- **Chosen option:** Option B — ChangesetBundle + approval gate.
- **Rationale:** pm-bot’s core value depends on trust. The safest path is to make **all writes an explicit, reviewable, auditable act**.
- **Trade-offs:** we accept extra state/UX work for a much smaller blast radius.
- **Scope of adoption:** applies to all mutating GitHub operations (issues/projects/relationships). Read-only operations remain ungated.

## Consequences

### Positive

- You can safely run pm-bot against real repos without fear of accidental mutation.
- Agents can be integrated later because “agent output == proposal”, never direct write.
- Idempotency is easier: proposals can be deduplicated and re-run safely.

### Negative / mitigations

- Requires a first-class approval interface.
  - Mitigation: start with a simple CLI approval flow; add UI later.
- Adds a local DB dependency to store bundles/approvals/audit logs.
  - Mitigation: start with SQLite (already used) and keep schemas simple.

### Migration plan

1. Ensure all existing write paths in `github_connector.py` are only reachable from “apply approved bundle”.
2. Add a policy layer:
   - unknown operations denied by default
   - repo allowlist enforced
3. Add a runbook validation gate:
   - “attempt unapproved write must be denied”
4. Add audit event logging for:
   - proposed, approved, applied, failed, denied

### Test strategy

- Unit tests:
  - bundle generation determinism
  - idempotency key stability
- Integration tests (sandbox):
  - denied write without approval
  - applied write with approval
- Human runbook:
  - `docs/runbooks/first-human-test.md`

### Docs updates required

- `docs/contracts/changesets.md`
- `docs/runbooks/first-human-test.md`
- `STATUS.md` scope bullets for any behavior change

## Alternatives considered (but not chosen)

- “Soft approval” (warn but allow write): rejected as too easy to bypass.

## Open questions

- Should approvals be per-changeset or per-bundle by default?
- Should a bundle support partial approval (approve some changesets, reject others)?

## References

- `docs/contracts/changesets.md`

## Changelog

- 2026-02-22 — Proposed by @you

