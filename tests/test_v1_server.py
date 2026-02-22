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

    with pytest.raises(PermissionError):
        app.propose_changeset(
            operation="update_issue",
            repo="untrusted/repo",
            payload={"title": "Nope"},
        )


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
