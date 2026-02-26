# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
### Added
- Plan Intake guided workflow in the GUI for natural-text planning with explicit `report-ir` stages: intake draft, human confirm, deterministic preview, and approval-gated propose handoff.
- `report-ir` API surfaces and typed UI client contracts for draft/confirm/preview/propose responses, including deterministic dependency-preview payloads.
- Unified inbox (`inbox/v1`) aggregation across pm-bot approvals and GitHub triage/review items, with deterministic merge ordering and diagnostics.
- Onboarding readiness endpoints for operators (`GET /onboarding/readiness`, `POST /onboarding/dry-run`) and corresponding CLI parity behavior.
- Multi-agent audit operations endpoints: `audit_chain/v1`, `audit_rollups/v1`, and `incident_bundle/v1` for run-level traceability and incident export.
- Runner adapter portability baseline and lifecycle controls, including adapter contract operations (`submit/poll/fetch_artifacts/cancel`) and queue/claim metadata.
- Context pack v2 contract surfaces: canonical hash rules, deterministic budget behavior, and inclusion/exclusion/redaction/provenance manifests.
- v2 estimator service with deterministic P50/P80 snapshots and fallback predictions.
- v2 graph service for tree and dependency views.
- v2 weekly report generator and report persistence metadata.
- CLI `pm parse --url` support.
- Expanded tests for v2 server features and CLI parse validation.

### Changed
- Agent run lifecycle semantics now define normalized statuses, allowed transitions, and deterministic rejection reason codes for invalid state changes.
- Reporting spec now includes org-sensitive safety counters and v6 multi-agent rollup/risk slices tied to audit metadata.
- v6 roadmap status now records shipped Plan Intake GUI route and guided intake/confirm/preview/propose interactions, while noting remaining end-to-end Inbox approval/apply evidence for full closure.

### Fixed
- Plan Intake proposing flow now blocks proposal submission when preview validation errors are present, preventing invalid dependency previews from entering the approval queue.
