# Contract: RunArtifact/v1
> **Audience:** Contributors implementing run interrupt/artifact control-plane contracts.
> **Depth:** L3 (normative contract).
> **Source of truth:** Authoritative artifact metadata contract for run outputs.

Artifact metadata emitted by a run and stored in control-plane state.

Required fields: `artifact_id`, `run_id`, `kind`, `uri`, `metadata`.
