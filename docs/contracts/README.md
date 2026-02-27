# Contracts
> **Audience:** Contributors authoring or reviewing contract documents.
> **Depth:** L3 (contract index).
> **Source of truth:** Canonical index for contract documents; normative contract truth lives in linked L3 docs and schemas.


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
- AgentRunSpec v2: [`agent_run_spec_v2.md`](agent_run_spec_v2.md)
- ContextPack v1: [`context_pack.md`](context_pack.md)
- LLM Capabilities: [`llm_capabilities.md`](llm_capabilities.md)



## Validation contract (CLI parse/draft)

`pm parse --validate` and `pm draft --validate` enforce a two-layer validation contract:

1. **JSON Schema validation** against `pm_bot/schema/work_item.schema.json`.
2. **Business-rule validation** for deterministic semantics not expressible in schema alone.

Validation failures MUST be emitted as machine-readable JSON:

```json
{
  "errors": [
    {
      "code": "SCHEMA_REQUIRED",
      "path": "$.area",
      "message": "'area' is a required property"
    }
  ]
}
```

Error objects MUST include stable fields:

- `code`: stable identifier (`SCHEMA_*` / `RULE_*`) suitable for automation.
- `path`: JSONPath-like pointer into the WorkItem payload.
- `message`: human-readable diagnostic text.

Determinism requirements:

- Error arrays MUST be sorted stably (`code`, `path`, `message`).
- Re-running validation on unchanged input MUST yield byte-for-byte equivalent error payloads.
