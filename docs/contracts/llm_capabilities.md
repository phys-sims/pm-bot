# LLM Capability Output Contracts

pm-bot capability orchestration is contract-first for all LLM-backed outputs under `pm_bot/schema/llm/`.

## Capability schemas

- `report_ir_draft` → `pm_bot/schema/llm/report_ir_draft.schema.json`
- `board_strategy_review` → `pm_bot/schema/llm/board_strategy_review.schema.json`
- `issue_replanner` → `pm_bot/schema/llm/issue_adjustment_proposal.schema.json`
- `issue_adjustment_proposal` → `pm_bot/schema/llm/issue_adjustment_proposal.schema.json`

## Prompt registry and orchestration requirements (normative)

Prompt templates are versioned and file-backed under `pm_bot/server/llm/prompts/` using one file per capability/version (for example `report_ir_draft.v1.md`).

When `run_capability(...)` executes a provider-backed capability, orchestration MUST:

1. Load prompt text from the prompt registry for the requested capability version.
2. Parse model output as **JSON object only**.
3. Validate parsed payload against the capability schema.
4. Return structured validation payloads with deterministic `errors` and `warnings` arrays.
5. Reject non-conforming outputs before any propose/apply write path is entered.

Validation errors are deterministic records:

- `path`: JSON-path-like location
- `code`: stable machine code (`JSON_*`, `SCHEMA_*`)
- `message`: human-readable description


## Capability classes and policy gates (normative)

Capabilities are grouped into explicit classes:

- `read_only_advice` (for example board analysis and prioritization suggestions).
- `mutation_proposal` (for example issue changes, reparenting, relabeling, body edits).

Orchestration MUST enforce class policy before provider execution:

1. `read_only_advice` runs may use low-friction approval policy (`approval_level=low`).
2. `mutation_proposal` runs MUST set `proposal_output_changeset_bundle=true` and `require_human_approval=true`.
3. `mutation_proposal` outputs MUST validate as ChangesetBundle-compatible proposal payloads.
4. No capability may enable direct GitHub write paths (`allow_direct_github_writes` is denied).

Policy violations return deterministic error codes with prefix
`capability_policy_denied:<capability_id>:...`.

## Error response contract

If capability output fails parse/schema validation, orchestration raises
`capability_output_validation_failed:<capability_id>` and returns:

```json
{
  "error": "capability_output_validation_failed:report_ir_draft",
  "capability_id": "report_ir_draft",
  "validation": {
    "errors": [
      {
        "path": "$.draft",
        "code": "SCHEMA_REQUIRED",
        "message": "'draft' is a required property"
      }
    ],
    "warnings": []
  }
}
```

This contract is validated by capability unit tests and server HTTP contract tests.


## Audit metadata contract

For each capability run, audit metadata MUST persist these fields so behavior can be traced/replayed:

- `capability_id`
- `prompt_version`
- `model` and `provider` (or normalized `model_provider`)
- `input_hash`
- `schema_version`
- `run_id`

Server audit endpoints (`/audit/chain`, `/audit/rollups`, `/audit/incident-bundle`) expose this metadata via event payloads and rollup concentration slices.
