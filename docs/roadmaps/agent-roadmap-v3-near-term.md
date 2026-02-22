# Agent Roadmap v3 Near-Term — Post-v2 Hardening + Docs/Contract Alignment + Operability
_Date: 2026-02-22_

## Stage boundary
### In scope
- Documentation authority consolidation across README/docs/spec/contracts/status references.
- ADR index/path consistency and broken-link elimination.
- Contract/spec de-duplication and contradiction cleanup.
- Operability quality gates (CI/reporting hygiene, deterministic checks, status update hygiene).

### Out of scope
- Multi-tenant architecture, billing, or org installation flows.
- New external integrations beyond current GitHub surface.
- Major schema contract expansion unrelated to alignment/hardening.

### Dependencies
- `STATUS.md` current health snapshot and roadmap taxonomy.
- `docs/adr/INDEX.md` and relevant ADRs for contracts/docs/ops tags.
- Canonical inputs under `vendor/dotgithub/` and work item schema.
- Existing contracts/specs in `docs/contracts/` and `docs/spec/`.

### Exit criteria
- Documentation precedence and navigation are internally consistent and testable.
- No duplicate/contradictory behavior statements across specs/contracts.
- CI quality gates are explicit, repeatable, and reflected in `STATUS.md`.

### Owner type
- Mixed (agent implementation + human approval for policy/document authority decisions).

## Mission
Harden the existing v0-v2 foundation so agents execute deterministic tasks against a single authoritative docs/contracts surface with reliable operational checks.

## Codex-sized implementation slices (1–2 days each)
1. **Docs authority pass**
   - Normalize start points and roadmap taxonomy in root/docs readmes.
   - Add explicit “active stage” guidance for agents.
2. **ADR index and path hygiene**
   - Validate ADR links and tags.
   - Fix path drift between docs references and file locations.
3. **Contract/spec de-dup pass**
   - Remove duplicated field semantics and link to single canonical definitions.
   - Add contradiction-check checklist in maintenance docs.
4. **Operability gate hardening**
   - Ensure lint/test/format/report commands are documented and enforced in CI docs.
   - Add measurable reporting hygiene checks.

## KPIs
- Zero broken markdown links in docs/roadmaps/spec/contracts.
- Zero contradictory field definitions for canonical labels (`Area`, `Priority`, `Size`, `Estimate (hrs)`, `Risk`, `Blocked by`, `Actual (hrs)`).
- CI checklist freshness in `STATUS.md` updated within same PR that changes behavior/docs gates.

## Required checks
- `pytest -q`
- `ruff check .`
- `ruff format .`

## Rollout and rollback
- Rollout: merge in small PRs by slice; keep each slice independently releasable.
- Rollback: revert doc-taxonomy/hygiene commits independently; preserve contracts/schemas unless explicitly changed.

## Acceptance criteria
- Active sequencing points to near-term stage by default.
- `STATUS.md` reflects roadmap taxonomy and active stage.
- Docs updates include citations/links to contracts/spec/ADR index where claims are made.
