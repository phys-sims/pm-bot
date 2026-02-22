# Examples

This folder contains **canonical example payloads** for pm-bot’s contracts.

These files should be kept in sync with:

- `docs/contracts/*`
- any JSON Schemas in `pm_bot/schema/*`

Recommended practice:

- add a CI test that validates each `*.example.json` file against its schema
- treat example drift as a failing test

Files:

- `report_ir_v1.example.json` — input plan format
- `workgraph.example.json` — normalized graph format
- `changeset_bundle.example.json` — proposed writes + approvals
- `agent_run_spec.example.json` — token-spend proposal format
- `context_pack.example.json` — deterministic context bundle format

