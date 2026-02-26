# ContextPack contract
> **Audience:** Contributors implementing context-pack composition/consumption.
> **Depth:** L3 (normative contract).
> **Source of truth:** Authoritative contract semantics for ContextPack payloads.


## Versions

- Current: `context_pack/v2`
- Compatibility: `context_pack/v1` remains supported for callers that request it explicitly.

Breaking shape changes require a new schema version.

## v2 goals (normative)

`context_pack/v2` MUST be:

- deterministic for identical inputs,
- budgeted by explicit `max_chars`,
- hash-stable using canonical JSON serialization,
- auditable via inclusion/exclusion/redaction manifests,
- safe against accidental secret leakage through deterministic redaction.

## Canonical serialization and hash contract

For v2 hash computation:

1. Build the payload object **without** the `hash` field.
2. Serialize with JSON keys sorted lexicographically and compact separators (`,`, `:`), UTF-8.
3. Compute `sha256` hex digest over that exact byte stream.
4. Set `hash` to the resulting 64-char lowercase hex string.

## v2 top-level shape

Required top-level fields:

- `schema_version`: literal `context_pack/v2`
- `profile`: context profile
- `root.issue_ref`: root work-item reference
- `budget`: `{max_chars, used_chars, strategy}`
- `sections[]`: included segments in deterministic rank order
- `manifest`: inclusion/exclusion/redaction/provenance ledger
- `hash`: canonical hash of payload-without-hash

Optional:

- `content`: compatibility convenience copy of root segment payload when available

## Deterministic budget behavior

Builder MUST:

- rank segment candidates deterministically,
- include in rank order until budget would be exceeded,
- exclude overflow segments with reason code `budget_exceeded`,
- never emit `used_chars > max_chars`.

## Redaction and provenance manifest

Builder MUST:

- redact values matching configured secret-like patterns,
- emit only category/count metadata (never original secret values),
- include provenance entries that map included segment IDs to source issue refs.

Manifest fields:

- `included_segments[]`
- `excluded_segments[]` with machine-readable reason codes
- `exclusion_reasons` aggregated counts
- `redaction_counts` (`total` + per-category counts)
- `provenance[]`

## v1 compatibility mapper

When callers request `context_pack/v1`, the server may return the legacy payload shape.

For compatibility workflows that ingest historic v1 payloads, a mapper to v2 semantics is available (`map_v1_to_v2`) and produces:

- `schema_version: context_pack/v2`
- a single `root.v1-content` section
- deterministic budget and manifest metadata
- hash continuity using either provided v1 hash or canonical v2 hash fallback

## Schema artifact

JSON Schema for v2 is tracked at:

- `pm_bot/schema/context_pack_v2.schema.json`
