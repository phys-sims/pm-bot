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
