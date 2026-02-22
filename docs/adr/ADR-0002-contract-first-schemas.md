# Contract-first core objects: ReportIR, WorkGraph, Changesets, AgentRunSpec

- **ADR ID:** ADR-0002
- **Status:** Proposed
- **Date:** 2026-02-22
- **Deciders:** @you
- **Area:** contracts
- **Related:** `pm_bot/schema/work_item.schema.json`, `pm_bot/server/context_pack.py`, `pm_bot/server/changesets.py`
- **Tags:** contracts, idempotency, safety, schemas, docs
- **Scope:** repo
- **Visibility:** public

## Context

pm-bot is an “agent-native work orchestrator” spanning:

- human planning inputs (Markdown, paragraphs)
- deterministic rendering into GitHub templates
- safe application of writes to GitHub
- optional agent execution

Without explicit contracts, the system will drift:

- agents will “guess” data shapes
- schema changes will break downstream steps silently
- idempotency becomes accidental rather than designed

## Options considered

### Option A — Implicit contracts (Python objects only)

- **Description:** rely on internal Python models, no explicit schema/doc boundary.
- **Pros:**
  - fast to implement
  - no duplicated work
- **Cons:**
  - hard for agents to reason about the system without reading code
  - changes ripple unpredictably
  - difficult to validate external inputs (reports) deterministically
- **Risks / Unknowns:**
  - subtle bugs when models evolve
- **Testing impact:**
  - fewer opportunities for fixture-driven validation

### Option B — Contract-first with explicit versioned objects + examples

- **Description:** define stable versioned contracts for each major stage:
  - ReportIR: extracted plan
  - WorkGraph: normalized graph
  - ChangesetBundle: proposed writes
  - AgentRunSpec: proposed token spend
- **Pros:**
  - agents can implement steps mechanically
  - idempotency keys and stable IDs become part of the contract
  - fixture-driven tests catch drift early
  - enables deterministic “preview diffs”
- **Cons:**
  - requires writing docs + schemas + examples
  - requires explicit versioning decisions
- **Risks / Unknowns:**
  - can be over-designed if scope explodes
  - needs discipline to keep docs/examples in sync
- **Testing impact:**
  - enables CI validation of examples against schemas

## Decision

- **Chosen option:** Option B — contract-first core objects.
- **Rationale:** pm-bot’s value is reliability. Versioned contracts are the most scalable way to keep humans and agents aligned.
- **Trade-offs:** we accept slightly more up-front documentation work to reduce long-term drift and debugging cost.
- **Scope of adoption:** applies to the full plan → graph → changes → apply pipeline and to agent orchestration.

## Consequences

### Positive

- Agents have a clear “API” for what to read/write.
- Idempotency can be designed (stable IDs, idempotency keys) rather than hoped for.
- You can add new frontends/backends by targeting WorkGraph and Changesets.

### Negative / mitigations

- Requires maintenance discipline.
  - Mitigation: add CI that validates example JSON against schemas.
- Risk of premature abstraction.
  - Mitigation: keep v1 contracts minimal and add optional fields as needed.

### Migration plan

1. Document contracts in `docs/contracts/*`.
2. Add example payloads in `docs/examples/*`.
3. Add schema validation tests (CI) for examples.
4. Integrate parsing/validation into ingestion pipeline:
   - ReportIR parse → validate → map → changeset bundle

### Test strategy

- Contract tests: validate examples against schemas.
- Round-trip tests: parse/render stability for GitHub issue bodies.
- Integration tests: bundle preview matches applied results.

### Docs updates required

- `docs/contracts/*`
- `docs/examples/*`
- `docs/maintenance.md`

## Alternatives considered (but not chosen)

- “Only WorkItem schema, no higher-level contracts”: rejected because it leaves plan ingestion and changesets underspecified.

## Open questions

- Should ReportIR embed “repo hints” (preferred repo per item) in v1?
- Should WorkGraph be stored as a separate schema from WorkItem, or derived entirely?

## References

- `docs/contracts/README.md`

## Changelog

- 2026-02-22 — Proposed by @you

