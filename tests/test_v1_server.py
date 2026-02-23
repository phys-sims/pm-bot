import pytest

from pm_bot.server.app import create_app


def test_changesets_require_approval_before_write():
    app = create_app()

    changeset = app.propose_changeset(
        operation="update_issue",
        repo="phys-sims/phys-pipeline",
        target_ref="#42",
        payload={"title": "New title"},
    )
    assert changeset["status"] == "pending"

    approval = app.approve_changeset(changeset["id"], approved_by="human-reviewer")
    assert approval["status"] == "applied"


def test_changeset_repo_guardrail_enforced():
    app = create_app()

    with pytest.raises(PermissionError, match="repo_not_allowlisted"):
        app.propose_changeset(
            operation="update_issue",
            repo="untrusted/repo",
            payload={"title": "Nope"},
        )

    denied_events = app.db.list_audit_events("changeset_denied")
    assert denied_events
    assert denied_events[0]["payload"]["reason_code"] == "repo_not_allowlisted"


def test_changeset_operation_denylist_reason_code():
    app = create_app()

    with pytest.raises(PermissionError, match="operation_denylisted"):
        app.propose_changeset(
            operation="delete_issue",
            repo="phys-sims/phys-pipeline",
            payload={"issue_ref": "#10"},
        )

    denied_events = app.db.list_audit_events("changeset_denied")
    assert denied_events
    assert denied_events[0]["payload"]["reason_code"] == "operation_denylisted"


def test_context_pack_returns_hash():
    app = create_app()

    draft = app.draft(item_type="feature", title="Parser", body_fields={"Goal": "Ship parser"})
    issue_ref = draft["issue_ref"]

    ctx = app.context_pack(issue_ref)
    assert ctx["hash"]
    assert ctx["content"]["fields"]["Goal"] == "Ship parser"


def test_connector_read_endpoints_after_approved_write():
    app = create_app()

    create_changeset = app.propose_changeset(
        operation="create_issue",
        repo="phys-sims/phys-pipeline",
        payload={"issue_ref": "#77", "title": "Ingest events", "area": "platform"},
    )
    app.approve_changeset(create_changeset["id"], approved_by="reviewer")

    issue = app.fetch_issue("phys-sims/phys-pipeline", "#77")
    assert issue is not None
    assert issue["title"] == "Ingest events"

    issues = app.list_issues("phys-sims/phys-pipeline", area="platform")
    assert len(issues) == 1


def test_connector_link_issue_write_is_applied():
    app = create_app()

    create_changeset = app.propose_changeset(
        operation="create_issue",
        repo="phys-sims/phys-pipeline",
        payload={"issue_ref": "#77", "title": "Ingest events", "area": "platform"},
    )
    app.approve_changeset(create_changeset["id"], approved_by="reviewer")

    link_changeset = app.propose_changeset(
        operation="link_issue",
        repo="phys-sims/phys-pipeline",
        target_ref="#77",
        payload={"linked_issue_ref": "#76", "relationship": "blocked_by"},
    )
    app.approve_changeset(link_changeset["id"], approved_by="reviewer")

    issue = app.fetch_issue("phys-sims/phys-pipeline", "#77")
    assert issue is not None
    assert issue["linked_issues"] == ["#76"]


def test_webhook_ingestion_upserts_work_item():
    app = create_app()
    result = app.ingest_webhook(
        "issues",
        {
            "repository": {"full_name": "phys-sims/phys-pipeline"},
            "issue": {
                "number": 42,
                "title": "Hook event",
                "state": "open",
                "labels": [{"name": "area:platform"}],
            },
        },
    )

    assert result["status"] == "ingested"
    work_item = app.get_work_item("phys-sims/phys-pipeline#42")
    assert work_item is not None
    assert work_item["fields"]["title"] == "Hook event"


def test_webhook_ingestion_with_api_connector_still_upserts_work_item() -> None:
    from pm_bot.server.github_auth import GitHubAuth
    from pm_bot.server.github_connector_api import GitHubAPIConnector

    app = create_app()
    app.connector = GitHubAPIConnector(auth=GitHubAuth(read_token=None, write_token="token"))

    result = app.ingest_webhook(
        "issues",
        {
            "repository": {"full_name": "phys-sims/phys-pipeline"},
            "issue": {
                "number": 51,
                "title": "Webhook API mode",
                "state": "open",
                "labels": [{"name": "area:platform"}],
            },
        },
    )

    assert result["status"] == "ingested"
    work_item = app.get_work_item("phys-sims/phys-pipeline#51")
    assert work_item is not None
    assert work_item["fields"]["title"] == "Webhook API mode"


def test_non_retryable_write_failure_marks_changeset_failed_and_audits() -> None:
    app = create_app()
    changeset = app.propose_changeset(
        operation="create_issue",
        repo="phys-sims/phys-pipeline",
        payload={"issue_ref": "#100", "title": "Will fail"},
    )

    def _fail(_request: object) -> dict[str, object]:
        raise RuntimeError("HTTP 401")

    app.connector.execute_write = _fail  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="non_retryable_failure"):
        app.approve_changeset(changeset["id"], approved_by="reviewer", run_id="run-hard-fail")

    stored = app.db.get_changeset(changeset["id"])
    assert stored is not None
    assert stored["status"] == "failed"

    attempts = app.db.list_audit_events("changeset_attempt")
    assert attempts[-1]["payload"]["result"] == "failure"
    assert attempts[-1]["payload"]["reason_code"] == "write_failed"

    dead_letters = app.db.list_audit_events("changeset_dead_lettered")
    assert dead_letters[-1]["payload"]["reason_code"] == "non_retryable_failure"
    assert dead_letters[-1]["payload"]["run_id"] == "run-hard-fail"


def test_v2_estimator_snapshot_and_predict_fallback():
    app = create_app()
    app.db.upsert_work_item(
        "phys-sims/phys-pipeline#1",
        {
            "title": "A",
            "type": "task",
            "area": "platform",
            "size": "m",
            "actual_hrs": 4.0,
            "fields": {},
            "relationships": {"children_refs": []},
        },
    )
    app.db.upsert_work_item(
        "phys-sims/phys-pipeline#2",
        {
            "title": "B",
            "type": "task",
            "area": "platform",
            "size": "m",
            "actual_hrs": 8.0,
            "fields": {},
            "relationships": {"children_refs": []},
        },
    )

    snapshots = app.estimator_snapshot()
    assert snapshots

    prediction = app.estimate(item_type="task", area="platform", size="m")
    assert prediction["p50"] == 4.0
    assert prediction["p80"] == 8.0


def test_v2_graph_tree_and_dependencies():
    app = create_app()
    parent = app.draft(item_type="epic", title="Root")
    child = app.draft(item_type="feature", title="Child")
    app.link_work_items(parent["issue_ref"], child["issue_ref"])

    tree = app.graph_tree(parent["issue_ref"])
    assert tree["issue_ref"] == parent["issue_ref"]
    assert tree["children"][0]["issue_ref"] == child["issue_ref"]

    app.db.upsert_work_item(
        "x#1",
        {
            "title": "Blocked",
            "type": "task",
            "area": "platform",
            "blocked_by": "x#0",
            "fields": {"issue_ref": "x#1"},
            "relationships": {"children_refs": []},
        },
    )
    deps = app.graph_deps(area="platform")
    assert deps["edges"][0]["edge_type"] == "blocked_by"


def test_v2_weekly_report_generation(tmp_path):
    app = create_app()
    app.reporting.reports_dir = tmp_path
    report = app.generate_weekly_report("weekly-test.md")
    assert report["status"] == "generated"
    assert report["report_path"].endswith("weekly-test.md")


def test_idempotent_propose_reuses_existing_changeset():
    app = create_app()

    first = app.propose_changeset(
        operation="update_issue",
        repo="phys-sims/phys-pipeline",
        target_ref="#42",
        payload={"title": "Stable"},
    )
    second = app.propose_changeset(
        operation="update_issue",
        repo="phys-sims/phys-pipeline",
        target_ref="#42",
        payload={"title": "Stable"},
    )

    assert first["id"] == second["id"]
    assert first["idempotency_key"] == second["idempotency_key"]


def test_retryable_write_succeeds_within_budget_and_records_metrics():
    app = create_app()
    changeset = app.propose_changeset(
        operation="create_issue",
        repo="phys-sims/phys-pipeline",
        payload={"issue_ref": "#90", "title": "Retry", "_transient_failures": 1},
        run_id="run-retry-success",
    )

    result = app.approve_changeset(
        changeset["id"], approved_by="reviewer", run_id="run-retry-success"
    )
    assert result["status"] == "applied"

    attempts = app.db.list_audit_events("changeset_attempt")
    assert len(attempts) == 2
    assert attempts[0]["payload"]["result"] == "retryable_failure"
    assert attempts[0]["payload"]["reason_code"] == "transient_failure"
    assert attempts[0]["payload"]["backoff_ms"] == 100
    assert attempts[1]["payload"]["result"] == "success"
    assert attempts[0]["payload"]["run_id"] == "run-retry-success"

    metrics = app.observability_metrics()
    outcomes = {(m["operation_family"], m["outcome"]) for m in metrics}
    assert ("changeset_write", "retryable_failure") in outcomes
    assert ("changeset_write", "success") in outcomes


def test_retry_budget_exhaustion_dead_letters_changeset():
    app = create_app()
    changeset = app.propose_changeset(
        operation="create_issue",
        repo="phys-sims/phys-pipeline",
        payload={"issue_ref": "#91", "title": "Fail", "_transient_failures": 9},
    )

    with pytest.raises(RuntimeError, match="retry_budget_exhausted"):
        app.approve_changeset(changeset["id"], approved_by="reviewer", run_id="run-dead-letter")

    stored = app.db.get_changeset(changeset["id"])
    assert stored is not None
    assert stored["status"] == "failed"
    assert stored["retry_count"] == 3

    dead_letters = app.db.list_audit_events("changeset_dead_lettered")
    assert dead_letters[0]["payload"]["reason_code"] == "retry_budget_exhausted"
    assert dead_letters[0]["payload"]["run_id"] == "run-dead-letter"


def test_run_id_correlation_for_webhook_and_reporting_events(tmp_path):
    app = create_app()
    app.reporting.reports_dir = tmp_path

    app.ingest_webhook(
        "issues",
        {
            "repository": {"full_name": "phys-sims/phys-pipeline"},
            "issue": {"number": 10, "title": "Traceable", "labels": []},
        },
        run_id="run-observe-1",
    )
    app.generate_weekly_report("obs.md", run_id="run-observe-1")

    webhook_event = app.db.list_audit_events("webhook_received")[0]
    report_event = app.db.list_audit_events("report_generated")[0]
    assert webhook_event["payload"]["run_id"] == "run-observe-1"
    assert report_event["payload"]["run_id"] == "run-observe-1"
