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
