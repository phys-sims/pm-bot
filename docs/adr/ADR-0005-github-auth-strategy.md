# Prefer GitHub App or PAT over Actions GITHUB_TOKEN for write operations

- **ADR ID:** ADR-0005
- **Status:** Proposed
- **Date:** 2026-02-22
- **Deciders:** @you
- **Area:** github
- **Related:** `pm_bot/server/github_connector.py`, `vendor/dotgithub/project-field-sync.yml`
- **Tags:** auth, github, safety, ops
- **Scope:** repo
- **Visibility:** public

## Context

pm-bot may run in multiple contexts:

- locally (CLI/server)
- as a GitHub Action (optional)

GitHub provides `GITHUB_TOKEN` to workflows, but it has limitations that can break automation chains:

- content created by `GITHUB_TOKEN` may not trigger other workflows

For pm-bot, this is particularly relevant if:

- pm-bot creates/issues updates issues and expects downstream workflows (like Projects sync) to run.

## Options considered

### Option A — Use Actions `GITHUB_TOKEN` for all writes

- **Pros:**
  - no extra secrets needed
  - easy setup
- **Cons:**
  - downstream workflows may not run
  - harder to scope to multiple repos/org-wide
- **Risks:**
  - silent failures: “issue created, but project fields never update”
- **Operational impact:**
  - debugging becomes painful

### Option B — Use a PAT for writes (personal-first)

- **Pros:**
  - predictable behavior (events trigger workflows normally)
  - easy to set up
- **Cons:**
  - tied to a human account
  - requires careful scoping and rotation
- **Operational impact:**
  - manageable for single-user

### Option C — Use a GitHub App for writes (org-scale)

- **Pros:**
  - least privilege at org scope
  - not tied to a human account
  - better long-term posture for multi-user
- **Cons:**
  - more initial setup
  - tokens expire and need refresh logic
- **Operational impact:**
  - best for always-on service

## Decision

- **Chosen option:** Option B for quick personal use, Option C as the long-term default.
- **Rationale:** pm-bot’s reliability depends on predictable event/workflow behavior and least privilege. `GITHUB_TOKEN` is great for lightweight automation, but risky for multi-step orchestration.
- **Scope of adoption:**
  - Write operations should not depend on `GITHUB_TOKEN` unless explicitly tested and accepted for that workflow chain.

## Consequences

### Positive

- Fewer “mysterious” workflow failures.
- Clear upgrade path from PAT → GitHub App.

### Negative / mitigations

- Requires secret management.
  - Mitigation: document setup; keep `.env` local; keep secrets in Actions secrets.

### Migration plan

1. Local-first:
   - allow PAT usage with repo allowlists
2. Service mode:
   - add GitHub App support
   - implement token refresh and webhook validation (if needed)
3. If Actions usage is desired:
   - allow explicit configuration per workflow (“PAT token step”)

### Test strategy

- Integration test in sandbox:
  - create issue via chosen auth
  - confirm downstream workflows trigger
- Runbook validation:
  - `docs/runbooks/first-human-test.md`

### Docs updates required

- `docs/github/auth-and-tokens.md`

## Open questions

- Should the connector support multiple credentials simultaneously (read vs write)?
- Do we need separate Apps for read-only vs write?

## References

- `docs/github/auth-and-tokens.md`

## Changelog

- 2026-02-22 — Proposed by @you

