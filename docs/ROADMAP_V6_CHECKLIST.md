# Roadmap v6 Execution Checklist — Natural-Text Planning + GUI Agent Ops + Multi-Agent Audit

This checklist tracks execution of v6 tracks A–D from `docs/roadmaps/agent-roadmap-v6-multi-repo-orchestration.md`.

Legend: `☑ done`, `◐ in progress`, `☐ pending`, `⛔ blocked`.

| Order | Track | Item | Owner | Status | PR link | Blockers |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | A | A1 GUI route expansion (Agent Runs + Context Pack pages) | agent | ☑ done | — | none |
| 2 | A | A2 API client coverage for `/context-pack` + `/agent-runs/*` | agent | ☑ done | — | depends on A1 |
| 3 | A | A3 approval-preserving UI action guards and reason-code rendering | agent | ☑ done | — | depends on A2 |
| 4 | B | B1 natural-text intake endpoint and audit envelope | agent | ☑ done | — | none |
| 5 | B | B2 LLM-assisted `report_ir/v1` draft generation + validation feedback | agent | ☑ done | — | depends on B1 |
| 6 | B | B3 human edit/confirm checkpoint for generated ReportIR | agent | ☑ done | — | depends on B2 |
| 7 | B | B4 deterministic ReportIR → multi-repo changeset preview | agent | ☑ done | — | depends on B3 |
| 8 | B | B5 approval handoff/idempotency integration with existing changeset engine | agent | ☑ done | — | depends on B4 |
| 9 | C | C1 GUI run-spec form + contract-aligned validation | agent | ☑ done | — | depends on A2 |
| 10 | C | C2 context-pack binding UX (hash/version + budget summary) | agent | ☑ done | — | depends on C1 |
| 11 | C | C3 lifecycle operations panel (transition controls + actor/reason) | agent | ☑ done | — | depends on C1 |
| 12 | C | C4 artifact/result visibility (job IDs, paths, retries, reason codes) | agent | ☑ done | — | depends on C3 |
| 13 | D | D1 audit-chain query API (`run_id`, event_type, repo, actor, window) | agent | ☑ done | — | depends on B5/C3 |
| 14 | D | D2 correlated timeline UI for run/context/changeset/report events | agent | ☑ done | — | depends on D1 |
| 15 | D | D3 multi-agent rollups (success/retry/dead-letter/denial distributions) | agent | ☑ done | — | depends on D1 |
| 16 | D | D4 runbook hooks + exportable incident bundles | agent | ☑ done | — | depends on D2/D3 |

## Gate checks required on every v6 slice

- `pytest -q`
- `ruff check .`
- `ruff format .`
- Relevant HTTP contract tests for touched endpoints.
- Relevant UI unit/e2e tests for touched routes.

## Exit gates for v6 closure

1. A user can complete natural-text intake → ReportIR confirm → multi-repo preview → approve flow from GUI.
2. A user can complete context-pack build + agent-run propose/approve/execute flow from GUI.
3. Multi-agent audit chain is queryable and visible by `run_id` with deterministic ordering.
4. Weekly report includes multi-agent operations rollups with sample sizes.
5. `STATUS.md` and roadmap/checklist statuses reflect the final state with no stale in-progress entries.

## Top risk register (keep current)

1. **Risk:** LLM draft nondeterminism causes unstable previews.
   - **Mitigation:** persist confirmed ReportIR and derive proposals only from confirmed artifact.
2. **Risk:** GUI actions accidentally bypass approval semantics.
   - **Mitigation:** action guards in UI + server-side approval invariant tests.
3. **Risk:** Audit payload expansion creates noisy/opaque operator views.
   - **Mitigation:** typed timeline sections + stable filtering/sorting keys.
4. **Risk:** API/UI contract drift as new routes are added quickly.
   - **Mitigation:** fixture-backed HTTP contract snapshots and typed frontend API models.
