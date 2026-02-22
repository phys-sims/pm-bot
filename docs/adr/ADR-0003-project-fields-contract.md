# Preserve Projects field sync via heading-value contract

- **ADR ID:** ADR-0003
- **Status:** Proposed
- **Date:** 2026-02-22
- **Deciders:** @you
- **Area:** github
- **Related:** `vendor/dotgithub/project-field-sync.yml`, `vendor/dotgithub/ISSUE_TEMPLATE/*.yml`, `pm_bot/github/render_issue_body.py`
- **Tags:** github, projects, templates, compatibility, safety
- **Scope:** repo
- **Visibility:** public

## Context

pm-bot’s GitHub Projects integration relies on an existing workflow that parses issue bodies.

The workflow’s behavior is sensitive to formatting:

- it reads headings
- it uses the first non-empty line under each heading as the field value

If pm-bot’s renderer drifts, the Project board becomes unreliable.

## Options considered

### Option A — Keep heading-based sync as the compatibility target

- **Description:** treat the current workflow as a hard external constraint; pm-bot must render headings accordingly.
- **Pros:**
  - minimal disruption to existing org workflows
  - keeps Projects sync logic centralized in GitHub Actions
  - leverages existing stable behavior (“worked months ago”)
- **Cons:**
  - brittle: formatting must be exact
  - limits creative formatting in issue bodies
- **Risks / Unknowns:**
  - template edits can break sync silently without tests
- **Testing impact:**
  - requires fixture-driven parser/renderer tests and a human runbook

### Option B — Replace with direct Projects GraphQL updates from pm-bot

- **Description:** stop depending on issue-body parsing; set Project fields directly via GraphQL.
- **Pros:**
  - avoids formatting brittleness
  - clearer separation between issue body and project metadata
- **Cons:**
  - moves complexity and auth into pm-bot
  - must handle rate limits and retries
  - requires distributing pm-bot auth to all environments that write
- **Risks / Unknowns:**
  - could become operationally heavy prematurely
- **Testing impact:**
  - requires more integration tests + sandbox environments

## Decision

- **Chosen option:** Option A for v0–v2.
- **Rationale:** the org already depends on the workflow and templates. Keeping compatibility lets pm-bot deliver value now with minimal operational burden.
- **Trade-offs:** we accept formatting constraints in exchange for not rewriting Projects automation.
- **Scope of adoption:** renderer and templates MUST preserve required headings and value placement.

## Consequences

### Positive

- pm-bot can remain local-first; Projects updates happen via repo workflows.
- Fewer privileged APIs in pm-bot itself.

### Negative / mitigations

- Formatting brittleness.
  - Mitigation:
    - deterministic renderer
    - compatibility tests
    - a dedicated doc (`docs/github/projects-field-sync.md`)
    - a “first human test” runbook

### Migration plan

If we later switch to direct Projects updates:

1. Write an ADR superseding this one.
2. Implement GraphQL add-item-then-update-field logic.
3. Keep heading-based rendering for readability, but stop treating it as a Projects contract.
4. Run both systems in parallel in a sandbox until stable.

### Test strategy

- Unit tests: render output includes required headings in correct format.
- Human runbook: create/edit issues and verify Project fields populate.

### Docs updates required

- `docs/github/projects-field-sync.md`
- `STATUS.md` compatibility notes

## Open questions

- Should we eventually store Project field values separately from issue bodies and render them only for human readability?
- Should templates be updated to eliminate legacy heading variants (`Size (Epic)`)?

## References

- `docs/github/projects-field-sync.md`

## Changelog

- 2026-02-22 — Proposed by @you

