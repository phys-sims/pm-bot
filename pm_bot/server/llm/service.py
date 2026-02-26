"""Unified capability runner for LLM-backed and deterministic server features."""

from __future__ import annotations

import json
from typing import Any

from pm_bot.server.llm.providers import LLMProvider, LLMRequest, LocalLLMProvider
from pm_bot.server.llm.registry import get_capability_definition


class CapabilityOutputValidationError(ValueError):
    """Raised when a provider output is not valid JSON for a capability contract."""

    def __init__(
        self,
        capability_id: str,
        *,
        errors: list[dict[str, str]],
        warnings: list[dict[str, str]],
    ) -> None:
        self.capability_id = capability_id
        self.errors = errors
        self.warnings = warnings
        super().__init__(f"capability_output_validation_failed:{capability_id}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "error": str(self),
            "capability_id": self.capability_id,
            "validation": {
                "errors": self.errors,
                "warnings": self.warnings,
            },
        }


def _select_provider(context: dict[str, Any], providers: dict[str, LLMProvider]) -> LLMProvider:
    provider_name = str(context.get("provider", "local")).strip() or "local"
    provider = providers.get(provider_name)
    if provider is None:
        raise ValueError(f"unknown_provider:{provider_name}")
    return provider


def _enforce_guardrails(
    *, capability_id: str, input_payload: dict[str, Any], guardrails: dict[str, Any]
) -> None:
    if (
        guardrails.get("require_natural_text")
        and not str(input_payload.get("natural_text", "")).strip()
    ):
        raise ValueError(f"capability_guardrail_failed:{capability_id}:missing_natural_text")
    if guardrails.get("require_org") and not str(input_payload.get("org", "")).strip():
        raise ValueError(f"capability_guardrail_failed:{capability_id}:missing_org")


def _parse_output_json_only(raw_text: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    if not raw_text.strip():
        return {}, [{"path": "$", "code": "JSON_EMPTY", "message": "model output is empty"}]
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return {}, [
            {
                "path": "$",
                "code": "JSON_PARSE",
                "message": f"model output is not valid JSON: {exc.msg}",
            }
        ]
    if not isinstance(parsed, dict):
        return {}, [
            {
                "path": "$",
                "code": "JSON_TYPE",
                "message": "model output must be a JSON object",
            }
        ]
    return parsed, []


def _validate_json_schema(
    payload: Any,
    schema: dict[str, Any],
    *,
    path: str = "$",
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    schema_type = schema.get("type")
    if schema_type == "object":
        if not isinstance(payload, dict):
            errors.append(
                {
                    "path": path,
                    "code": "SCHEMA_TYPE",
                    "message": "value must be an object",
                }
            )
            return errors, warnings

        required = schema.get("required", [])
        for field in sorted(required):
            if field not in payload:
                errors.append(
                    {
                        "path": f"{path}.{field}",
                        "code": "SCHEMA_REQUIRED",
                        "message": f"'{field}' is a required property",
                    }
                )

        properties = schema.get("properties", {})
        additional_properties = schema.get("additionalProperties", True)
        for key in sorted(payload.keys()):
            key_path = f"{path}.{key}"
            if key in properties:
                child_errors, child_warnings = _validate_json_schema(
                    payload[key], properties[key], path=key_path
                )
                errors.extend(child_errors)
                warnings.extend(child_warnings)
            elif additional_properties is False:
                errors.append(
                    {
                        "path": key_path,
                        "code": "SCHEMA_ADDITIONAL_PROPERTY",
                        "message": "additional properties are not allowed",
                    }
                )
        return errors, warnings

    if schema_type == "array":
        if not isinstance(payload, list):
            errors.append(
                {
                    "path": path,
                    "code": "SCHEMA_TYPE",
                    "message": "value must be an array",
                }
            )
            return errors, warnings
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(payload):
                child_errors, child_warnings = _validate_json_schema(
                    item, item_schema, path=f"{path}[{index}]"
                )
                errors.extend(child_errors)
                warnings.extend(child_warnings)
        return errors, warnings

    if schema_type == "string" and not isinstance(payload, str):
        errors.append({"path": path, "code": "SCHEMA_TYPE", "message": "value must be a string"})
        return errors, warnings

    if schema_type == "number" and not isinstance(payload, (int, float)):
        errors.append({"path": path, "code": "SCHEMA_TYPE", "message": "value must be a number"})
        return errors, warnings

    if schema_type == "integer" and not isinstance(payload, int):
        errors.append({"path": path, "code": "SCHEMA_TYPE", "message": "value must be an integer"})
        return errors, warnings

    if schema_type == "boolean" and not isinstance(payload, bool):
        errors.append({"path": path, "code": "SCHEMA_TYPE", "message": "value must be a boolean"})
        return errors, warnings

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and payload not in enum_values:
        errors.append(
            {
                "path": path,
                "code": "SCHEMA_ENUM",
                "message": f"value must be one of {enum_values}",
            }
        )
    return errors, warnings


def run_capability(
    capability_id: str,
    input_payload: dict[str, Any],
    context: dict[str, Any],
    policy: dict[str, Any],
    providers: dict[str, LLMProvider] | None = None,
) -> dict[str, Any]:
    """Execute a named capability through a normalized provider interface."""

    provider_map = providers or {"local": LocalLLMProvider()}
    definition = get_capability_definition(capability_id)
    _enforce_guardrails(
        capability_id=capability_id,
        input_payload=input_payload,
        guardrails=definition.guardrails,
    )

    provider = _select_provider(context, provider_map)
    request = LLMRequest(
        capability_id=capability_id,
        prompt=definition.prompt_template,
        input_payload=input_payload,
        context=context,
        policy=policy,
    )
    response = provider.run(request)
    parsed_output, parse_errors = _parse_output_json_only(response.raw_text)
    schema_errors, schema_warnings = _validate_json_schema(parsed_output, definition.output_schema)
    errors = sorted(parse_errors + schema_errors, key=lambda row: (row["code"], row["path"]))
    warnings = sorted(schema_warnings, key=lambda row: (row["code"], row["path"]))
    if errors:
        raise CapabilityOutputValidationError(
            capability_id=capability_id,
            errors=errors,
            warnings=warnings,
        )

    return {
        "capability_id": capability_id,
        "provider": response.provider,
        "model": response.model,
        "usage": response.usage,
        "output": parsed_output,
        "guardrails": definition.guardrails,
        "output_schema": definition.output_schema,
        "validation": {"errors": errors, "warnings": warnings},
    }
