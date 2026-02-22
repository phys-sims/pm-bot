**Title:** `<short, imperative> (e.g., Approval-gated writes via ChangesetBundles)>`

- **ADR ID:** `ADR-####`
- **Status:** `Proposed | Accepted | Rejected | Superseded by ADR-#### | Deprecated`
- **Date:** `YYYY-MM-DD`
- **Deciders:** `@handles, @reviewers`
- **Area:** `pm-bot | contracts | github | server | ui | db | ops | docs`
- **Related:** `Issue #123, PR #456, Project item link`
- **Tags:** `contracts, github, projects, safety, idempotency, tree, auth, testing, ops, docs`
- **Scope:** `repo | ecosystem`
- **Visibility:** `public | private`
- **Canonical ADR:** `<org/repo>/docs/adr/ADR-####.md (or path)>`
- **Impacted repos:** `pm-bot, .github, phys-pipeline, ... (if applicable)`
- **Related ecosystem ADRs:** `ECO-#### (link), ECO-#### (link)` *(if scope=repo and depends on ecosystem)*

### Context
- **Problem statement.** Why decide now? What requirement or constraint forces this?
- **In/Out of scope.** What this ADR governs, and what it explicitly does not.
- **Constraints.** Compatibility (templates/Projects sync), safety (approvals), cost (tokens), ops (rate limits).

### Options Considered
> Capture at least 2 options, ideally 3. Repeat the rubric below per option.

**Option A — `<name>`**
- **Description:** how it works
- **Impact areas:** data model, public API, algorithms, CI, docs
- **Pros:**
- **Cons:**
- **Risks / Unknowns:**
- **Perf/Resource cost:** runtime, memory, disk
- **Operational complexity:** maintenance, tooling, dev‑ex
- **Security/Privacy/Compliance:** (if any)
- **Dependencies / Externalities:** libs, infra, org process

**Option B — `<name>`**
- (same rubric)

**Option C — `<name>`** *(optional)*

### Decision
- **Chosen option:** A/B/C with rationale.
- **Trade‑offs:** what we accept/regret to gain benefits.
- **Scope of adoption:** where this applies (modules/repos), where exceptions are allowed.

### Consequences
- **Positive:** …
- **Negative / Mitigations:** …
- **Migration plan:** data/code changes, deprecations, feature flags, rollout steps.
- **Test strategy:** unit/contract/integration tests; success thresholds.
- **Monitoring & Telemetry:** metrics, dashboards, alerting, regression detection.
- **Documentation:** README/API docs/tutorial updates required.

### Alternatives Considered (but not chosen)
- Short bullets or links to spikes/experiments.

### Open Questions
- List unresolved items and owners.

### References
- Specs, prior ADRs, tickets, notebooks, benchmarks.

### Changelog
- `YYYY‑MM‑DD` — Proposed by @author
- `YYYY‑MM‑DD` — Accepted by @reviewers
- `YYYY‑MM‑DD` — Superseded by ADR-#### (link)

---
