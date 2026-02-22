# Local-first core with optional always-on service

- **ADR ID:** ADR-0006
- **Status:** Proposed
- **Date:** 2026-02-22
- **Deciders:** @you
- **Area:** ops
- **Related:** `pm_bot/cli.py`, `pm_bot/server/app.py`, `pm_bot/server/db.py`
- **Tags:** architecture, ops, safety
- **Scope:** repo
- **Visibility:** public

## Context

pm-bot needs to work in two realities:

1. **Local-first personal tool**
   - run on a laptop
   - no hosting required
   - low operational overhead

2. **Always-on service (future)**
   - webhooks, persistent state
   - org-scale controls
   - possible multi-user approvals

We want to avoid rewriting core logic when moving from (1) to (2).

## Options considered

### Option A — Always-on service from day one

- **Pros:**
  - first-class webhooks and realtime state
  - easier to share across users
- **Cons:**
  - operational overhead before value is proven
  - harder to adopt privately/publicly
- **Risks:**
  - scope creep, infrastructure distraction

### Option B — Local-first core with optional server layer

- **Description:** keep core logic as a library + CLI; add a thin server that uses the same contracts and code paths.
- **Pros:**
  - immediate usability
  - minimal ops burden
  - future hosting doesn’t require rewriting core pipeline
- **Cons:**
  - two run modes to keep consistent
- **Risks:**
  - drift between CLI and server if not tested

### Option C — CLI-only forever

- **Pros:**
  - minimal complexity
- **Cons:**
  - limited webhook integration
  - harder to build inbox, dashboards, or multi-user approval UX

## Decision

- **Chosen option:** Option B — local-first core + optional server.
- **Rationale:** maximize near-term value while preserving a clean upgrade path.
- **Scope of adoption:** all business logic should live in library modules; CLI and server should be thin shells.

## Consequences

### Positive

- Users can adopt pm-bot without hosting.
- Server mode can be added for org automation without rewriting parser/renderer/contracts.

### Negative / mitigations

- Risk of drift between CLI and server behavior.
  - Mitigation:
    - shared contract tests
    - shared service methods used by both
    - `STATUS.md` tracked health checks

### Migration plan

1. Ensure CLI is feature-complete for drafting/parsing/rendering.
2. Ensure server uses the same core modules, not duplicated logic.
3. Add runbooks that cover both modes.
4. If/when moving to hosted:
   - swap SQLite → Postgres
   - add auth/policy layers
   - keep contracts stable

### Test strategy

- Unit tests for core modules (parser/renderer/contracts).
- Server tests for approval gating and connector behaviors.
- Human runbook for end-to-end smoke.

### Docs updates required

- `docs/quickstart.md`
- `docs/runbooks/first-human-test.md`
- ADR index regeneration

## Open questions

- Should there be a “stateless mode” for CI usage (no DB)?
- How should configuration be shared between CLI and server (`.env`, config file, etc.)?

## References

- `docs/quickstart.md`
- `docs/maintenance.md`

## Changelog

- 2026-02-22 — Proposed by @you

