# QA Matrix: user-critical flows

This matrix maps user-critical flows to automated checks and manual runbook checks. CI release gating is tied to the automated commands listed here.

| Flow | User risk if broken | Automated checks | Manual check/runbook | CI job group | Release gate |
| --- | --- | --- | --- | --- | --- |
| Draft flow (`pm draft`) | Users cannot stage work items predictably for planning. | `pytest -q tests/test_runbook_scenarios.py` | `docs/runbooks/first-human-test.md` Step 2 (Parse → render round-trip) | `reliability-tests` | Required |
| Parse/render contract | Projects field sync and schema compatibility drift silently. | `pytest -q tests/test_server_http_contract.py tests/test_validation.py tests/test_github_connector_api.py` | `docs/runbooks/first-human-test.md` Step 1 + Step 2 | `contract-tests` | Required |
| Approval-gated writes | Unsafe writes can bypass review controls. | `pytest -q tests/test_runbook_scenarios.py` | `docs/runbooks/first-human-test.md` Step 3 | `reliability-tests` | Required |
| Idempotency on rerun | Duplicate issues/links are created under retries or reruns. | `pytest -q tests/test_runbook_scenarios.py` | `docs/runbooks/first-human-test.md` Step 4 | `reliability-tests` | Required |
| Reliability drills (retry/dead-letter) | Transient failures wedge execution or silently drop writes. | `pytest -q tests/test_runbook_scenarios.py` | `docs/runbooks/first-human-test.md` Step 7 | `reliability-tests` | Required |
| Regression fixtures (issue-body parse/render + reports) | Known-good outputs drift without detection. | `pytest -q tests/test_golden_issue_fixtures.py tests/test_reporting.py` | `docs/runbooks/first-human-test.md` Step 6 | `regression-fixtures` | Required |
| Docs/commands alignment | Runbooks and CI commands diverge; operators run stale checks. | `pytest -q tests/test_docs_commands.py` | Spot-check `docs/qa-matrix.md` and `.github/workflows/ci.yml` | `docs-command-validation` | Required |
| Docs hygiene gates (links/contradictions/status-operability) | Docs become non-authoritative and operators miss required gates. | `python scripts/docs_hygiene.py --check-links --check-contradictions --check-status-gates --check-depth-metadata --check-l0-bloat`; `pytest -q tests/test_docs_hygiene.py` | `docs/maintenance.md` contradiction-check workflow section | `docs-hygiene` | Required |

## Release gating policy

A release is blocked unless the `release-gate` CI job is green. The `release-gate` job requires:

1. `lint`
2. `contract-tests`
3. `reliability-tests`
4. `regression-fixtures`
5. `docs-command-validation`
6. `docs-hygiene`

The release gate enforces this matrix as the minimum quality bar for user-critical flows.
