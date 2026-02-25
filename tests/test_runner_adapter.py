import pytest

from pm_bot.server.app import create_app


def _minimal_spec(run_id: str, **extra: object) -> dict[str, object]:
    spec: dict[str, object] = {
        "run_id": run_id,
        "model": "gpt-5",
        "intent": "test",
        "requires_approval": True,
        "adapter": "manual",
    }
    spec.update(extra)
    return spec


def test_runner_transition_matrix_enforced() -> None:
    app = create_app()
    run = app.propose_agent_run(spec=_minimal_spec("run-1"), created_by="alice")
    assert run["status"] == "proposed"

    approved = app.transition_agent_run(
        run_id="run-1",
        to_status="approved",
        reason_code="human_approved",
        actor="reviewer",
    )
    assert approved["status"] == "approved"

    with pytest.raises(ValueError, match="invalid_transition:not_allowed"):
        app.transition_agent_run(
            run_id="run-1",
            to_status="completed",
            reason_code="skip",
            actor="reviewer",
        )


def test_runner_execute_manual_adapter_happy_path() -> None:
    app = create_app()
    app.propose_agent_run(spec=_minimal_spec("run-ok"), created_by="alice")
    app.transition_agent_run("run-ok", to_status="approved", reason_code="human_approved")

    claimed = app.claim_agent_runs(worker_id="w1", limit=2, lease_seconds=60)
    assert [item["run_id"] for item in claimed] == ["run-ok"]

    result = app.execute_claimed_agent_run(run_id="run-ok", worker_id="w1")
    assert result["status"] == "completed"

    artifacts = app.db.list_audit_events("agent_run_artifacts")
    assert artifacts[-1]["payload"]["run_id"] == "run-ok"


def test_runner_retry_and_dead_letter() -> None:
    app = create_app()
    app.propose_agent_run(
        spec=_minimal_spec("run-fail", manual_poll_state="failed", max_retries=1),
        created_by="alice",
    )
    app.transition_agent_run("run-fail", to_status="approved", reason_code="human_approved")

    claimed = app.claim_agent_runs(worker_id="w1", limit=1)
    assert claimed and claimed[0]["run_id"] == "run-fail"
    first = app.execute_claimed_agent_run(run_id="run-fail", worker_id="w1")
    assert first["status"] == "approved"

    app.db.conn.execute(
        "UPDATE agent_runs SET next_attempt_at = CURRENT_TIMESTAMP WHERE run_id = ?", ("run-fail",)
    )
    app.db.conn.commit()
    claimed_again = app.claim_agent_runs(worker_id="w1", limit=1)
    assert claimed_again and claimed_again[0]["run_id"] == "run-fail"
    second = app.execute_claimed_agent_run(run_id="run-fail", worker_id="w1")
    assert second["status"] == "failed"
    assert second["status_reason"] == "retry_budget_exhausted"

    dead = app.db.list_audit_events("agent_run_dead_lettered")
    assert dead[-1]["payload"]["run_id"] == "run-fail"
