# LLM Capability Output Contracts

pm-bot capability orchestration is contract-first for all LLM-backed outputs under `pm_bot/schema/llm/`.

## Capability schemas

- `report_ir_draft` → `pm_bot/schema/llm/report_ir_draft.schema.json`
- `board_strategy_review` → `pm_bot/schema/llm/board_strategy_review.schema.json`
- `issue_adjustment_proposal` → `pm_bot/schema/llm/issue_adjustment_proposal.schema.json`

## Orchestration requirements (normative)

When `run_capability(...)` executes a provider-backed capability, orchestration MUST:

1. Parse model output as **JSON object only**.
2. Validate parsed payload against the capability schema.
3. Return structured validation payloads with deterministic `errors` and `warnings` arrays.
4. Reject non-conforming outputs before any propose/apply write path is entered.

Validation errors are deterministic records:

- `path`: JSON-path-like location
- `code`: stable machine code (`JSON_*`, `SCHEMA_*`)
- `message`: human-readable description

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
