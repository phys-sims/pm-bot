# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
### Added
- Plan Intake guided workflow in the GUI for natural-text planning with explicit `report-ir` stages: intake draft, human confirm, deterministic preview, and approval-gated propose handoff.
- `report-ir` intake/confirm/preview/propose API surfaces and typed UI client contracts, including deterministic dependency-preview payloads.
- Unified inbox (`inbox/v1`) aggregation across pm-bot approvals and GitHub triage/review items, with deterministic merge ordering and diagnostics.
- Onboarding readiness surfaces for operators (`GET /onboarding/readiness`, `POST /onboarding/dry-run`) with CLI parity behavior.
- Multi-agent audit operations endpoints: `audit_chain/v1`, `audit_rollups/v1`, and `incident_bundle/v1` for run-level traceability and incident export.
- Runner adapter portability baseline with lifecycle controls, including adapter operations (`submit/poll/fetch_artifacts/cancel`) and queue/claim metadata.
- `context_pack/v2` contract and schema evolution with canonical hash rules, deterministic budgeting, and inclusion/exclusion/redaction/provenance manifests.
- v2 estimator service with deterministic P50/P80 snapshots and fallback predictions.
- v2 graph service for tree and dependency views.
- v2 weekly report generator and report persistence metadata.
- CLI `pm parse --url` support.

### Changed
- Agent run lifecycle now enforces normalized statuses, allowed transitions, and deterministic reason codes on invalid transitions.
- Reporting includes org-sensitive safety counters and v6 multi-agent rollup/risk slices tied to audit metadata.

### Fixed
- Plan Intake proposing flow now blocks submission when preview validation errors are present, preventing invalid dependency previews from entering approval queues.
