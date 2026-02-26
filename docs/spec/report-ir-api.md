# ReportIR HTTP API (`/report-ir/*`)
> **Audience:** Contributors implementing intake/confirmation/proposal workflows.
> **Depth:** L2 (behavioral specification).
> **Source of truth:** Normative HTTP behavior for implemented `/report-ir/*` routes; payload contracts remain defined at L3.

## Contract anchors

- ReportIR contract: [`docs/contracts/report_ir_v1.md`](../contracts/report_ir_v1.md)
- LLM capability contracts + validation/error model: [`docs/contracts/llm_capabilities.md`](../contracts/llm_capabilities.md)
- Changeset contract and approval semantics: [`docs/contracts/changesets.md`](../contracts/changesets.md)

All `/report-ir/*` routes return JSON only.

## `POST /report-ir/intake`

Generate a deterministic `report_ir` draft from natural text using the `report_ir_draft` capability.

### Request (required)

- `natural_text` (string, non-empty)
- `org` (string, non-empty)

### Request (optional)

- `repos` (string array)
- `run_id` (string)
- `requested_by` (string)
- `generated_at` (string)
- `mode` (string; default `basic`, supports `structured`)

### Success response (`200`)

- `draft_id` (string)
- `schema_version` = `report_ir_draft/v1`
- `draft` (object, MUST validate as `report_ir/v1`)
- `validation` (`errors[]`, `warnings[]`)

### Determinism and safety

- Capability output MUST pass schema validation before downstream proposal logic is invoked.
- Validation failures return deterministic machine-readable payloads (`path`, `code`, `message`).
- Intake MUST append audit event `report_ir_draft_generated` with `llm_metadata` (`capability_id`, `prompt_version`, `model`, `provider`, `input_hash`, `schema_version`, `run_id`).

### Error behavior

- `400 {"error":"invalid_json"}` for malformed JSON body.
- `400 {"error":"missing_required_fields"}` when `natural_text` or `org` are missing.
- `400` capability validation error payload (`capability_output_validation_failed:<capability_id>`) on schema-invalid model output.
- `500` fallback for unexpected exceptions.

## `POST /report-ir/confirm`

Validate and confirm a candidate `report_ir` payload before proposal/apply steps.

### Request (required)

- `report_ir` (object)
- `confirmed_by` (string, non-empty)

### Request (optional)

- `run_id` (string)
- `draft` (object, informational copy of draft payload)

### Success response (`200`)

- `status` = `confirmed`
- `confirmation_id` (deterministic from `generated_at` + normalized title)
- `validation` (`errors[]`, `warnings[]`)
- `report_ir` (echo of confirmed payload)

### Determinism and safety

- `report_ir` MUST validate with `validate_report_ir` and include `schema_version=report_ir/v1`.
- Confirmation MUST append audit event `report_ir_confirmed` containing actor, run id, confirmation id, draft copy, and confirmed payload.

### Error behavior

- `400 {"error":"invalid_json"}` for malformed JSON body.
- `400 {"error":"missing_required_fields"}` for missing `report_ir` or `confirmed_by`.
- `400 {"error":"report_ir_validation_failed"}` for contract violations.

## `POST /report-ir/preview`

Produce deterministic changeset preview output from a valid `report_ir` payload.

### Request (required)

- `report_ir` (object)

### Request (optional)

- `run_id` (string)

### Success response (`200`)

- `schema_version` = `changeset_preview/v1`
- `items[]` (deterministically sorted by `repo`, `stable_id`, `operation`)
- `dependency_preview.repos[]` with sorted `nodes[]` + `edges[]`
- `summary` (`count`, `repos[]`, `repo_count`)

### Determinism and safety

- Preview generation MUST be pure derivation from validated input (`report_ir`), with deterministic ordering and idempotency-key generation.
- Preview MUST append audit event `report_ir_preview_generated` with summary and run id.

### Error behavior

- `400 {"error":"invalid_json"}` for malformed JSON body.
- `400 {"error":"missing_report_ir"}` when `report_ir` is absent or non-object.
- `400 {"error":"report_ir_validation_failed"}` for contract violations.

## `POST /report-ir/propose`

Convert preview rows into proposed changesets (approval-gated write intent only).

### Request (required)

- `report_ir` (object)
- `run_id` (string, non-empty)
- `requested_by` (string, non-empty)

### Success response (`200`)

- `schema_version` = `report_ir_proposal/v1`
- `items[]`:
  - `stable_id`
  - `repo`
  - `idempotency_key`
  - `changeset` (created/reused proposal)
- `summary.count`

### Determinism and safety

- Propose MUST call preview first and preserve preview ordering.
- Per-item changeset creation MUST remain approval-gated and idempotency-keyed.
- Repeating the same proposal input SHOULD reuse existing changesets via idempotency semantics.
- Propose MUST append audit event `report_ir_changesets_proposed` with run id, actor, count, and changeset ids.

### Error behavior

- `400 {"error":"invalid_json"}` for malformed JSON body.
- `400 {"error":"missing_required_fields"}` for missing `report_ir`, `run_id`, or `requested_by`.
- `400 {"error":"report_ir_validation_failed"}` for contract violations.
- `403` guardrail denials propagate as `{ "error": "Changeset rejected by guardrails: ...", "reason_code": "..." }`.

## Shared response mapping

Across `/report-ir/*` routes, the ASGI adapter maps exceptions deterministically:

- `PermissionError` → `403`
- `CapabilityOutputValidationError` → `400`
- `ValueError` → `400`
- `RuntimeError` → `409`
- unexpected exception → `500`
