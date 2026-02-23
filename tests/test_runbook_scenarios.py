from __future__ import annotations

import pytest

from pm_bot.github.parse_issue_body import parse_issue_body
from pm_bot.github.render_issue_body import render_issue_body
from pm_bot.server.app import create_app
from pm_bot.server.github_connector import RetryableGitHubError


def test_runbook_flow_draft_parse_render_roundtrip() -> None:
    app = create_app()
    draft = app.draft(
        item_type="feature",
        title="Runbook flow",
        body_fields={
            "Goal": "Script runbook draft/parse/render flow",
            "Area": "platform",
            "Priority": "P1",
        },
    )

    rendered = render_issue_body(draft["work_item"])
    parsed = parse_issue_body(rendered, item_type="feature", title="Runbook flow")

    assert parsed["fields"]["Goal"] == "Script runbook draft/parse/render flow"
    assert parsed["area"] == "platform"
    assert parsed["priority"] == "P1"


def test_runbook_flow_approve_changeset() -> None:
    app = create_app()
    proposed = app.propose_changeset(
        operation="create_issue",
        repo="phys-sims/phys-pipeline",
        payload={"issue_ref": "#501", "title": "Approval drill"},
    )

    result = app.approve_changeset(proposed["id"], approved_by="qa-reviewer")

    assert result["status"] == "applied"


def test_runbook_flow_idempotency_reuses_existing_changeset() -> None:
    app = create_app()
    payload = {"issue_ref": "#502", "title": "Idempotency drill"}
    first = app.propose_changeset(
        operation="create_issue",
        repo="phys-sims/phys-pipeline",
        payload=payload,
    )
    second = app.propose_changeset(
        operation="create_issue",
        repo="phys-sims/phys-pipeline",
        payload=payload,
    )

    assert second["id"] == first["id"]
    reuse_events = app.db.list_audit_events("changeset_idempotent_reuse")
    assert reuse_events


def test_reliability_drill_retries_then_succeeds() -> None:
    app = create_app()
    proposed = app.propose_changeset(
        operation="create_issue",
        repo="phys-sims/phys-pipeline",
        payload={"issue_ref": "#503", "title": "Retry drill"},
    )

    attempts = {"count": 0}

    def _flaky(_request: object) -> dict[str, object]:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RetryableGitHubError(
                "rate limited", reason_code="github_rate_limited", retry_after_s=0
            )
        return {"status": "applied", "issue": {"number": 503}}

    app.connector.execute_write = _flaky  # type: ignore[method-assign]

    result = app.approve_changeset(proposed["id"], approved_by="qa-reviewer", run_id="run-retry")

    assert result["status"] == "applied"
    audit_attempts = app.db.list_audit_events("changeset_attempt")
    assert [entry["payload"]["result"] for entry in audit_attempts[-3:]] == [
        "retryable_failure",
        "retryable_failure",
        "success",
    ]


def test_reliability_drill_retry_budget_exhaustion_dead_letters() -> None:
    app = create_app()
    proposed = app.propose_changeset(
        operation="create_issue",
        repo="phys-sims/phys-pipeline",
        payload={"issue_ref": "#504", "title": "Dead-letter drill"},
    )

    def _always_retry(_request: object) -> dict[str, object]:
        raise RetryableGitHubError("flaky", reason_code="github_503", retry_after_s=0)

    app.connector.execute_write = _always_retry  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="retry_budget_exhausted"):
        app.approve_changeset(proposed["id"], approved_by="qa-reviewer", run_id="run-dead-letter")

    dead_letters = app.db.list_audit_events("changeset_dead_lettered")
    assert dead_letters[-1]["payload"]["reason_code"] == "retry_budget_exhausted"
