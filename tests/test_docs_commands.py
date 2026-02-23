from __future__ import annotations

from pathlib import Path


def test_qa_matrix_commands_are_listed_in_ci_jobs() -> None:
    matrix = Path("docs/qa-matrix.md").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    expected_commands = [
        "pytest -q tests/test_server_http_contract.py tests/test_validation.py tests/test_github_connector_api.py",
        "pytest -q tests/test_runbook_scenarios.py",
        "pytest -q tests/test_golden_issue_fixtures.py tests/test_reporting.py",
        "pytest -q tests/test_docs_commands.py",
    ]

    for command in expected_commands:
        assert command in matrix
        assert command in workflow
