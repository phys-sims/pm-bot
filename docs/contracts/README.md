# Contracts

This folder defines pm-bot’s core data contracts.

These contracts are intended to be:

- **stable across versions** (with explicit version bumps)
- **machine-validated** (JSON Schema / strict validation)
- **the bridge between humans, agents, and code**

If you change a contract, you must:

1. update the contract doc
2. update or add example JSON in `docs/examples/`
3. update schemas in `pm_bot/schema/` (if applicable)
4. add or update tests that validate examples against schemas

## Contracts

- ReportIR v1: [`report_ir_v1.md`](report_ir_v1.md)
- WorkGraph: [`workgraph.md`](workgraph.md)
- Changesets: [`changesets.md`](changesets.md)
- AgentRunSpec: [`agent_run_spec.md`](agent_run_spec.md)
- ContextPack v1: [`context_pack.md`](context_pack.md)

