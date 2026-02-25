import pytest

from pm_bot.server.app import create_app
from pm_bot.server.runner import RunnerAdapter, RunnerPollResult, RunnerSubmitResult
from pm_bot.server.runner_adapters import (
    registered_runner_adapters,
)
from pm_bot.server.runner_adapters.provider_stub import (
    ProviderStubRunnerAdapter,
    normalize_provider_failure,
)


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


@pytest.mark.parametrize(
    ("provider_reason", "expected"),
    [
        ("timeout", "provider_timeout"),
        ("rate_limit", "provider_rate_limited"),
        ("auth", "provider_auth_denied"),
        ("validation", "provider_invalid_request"),
        ("internal", "provider_unavailable"),
        ("unexpected", "provider_failed"),
    ],
)
def test_provider_failure_reason_normalization(provider_reason: str, expected: str) -> None:
    assert normalize_provider_failure(provider_reason) == expected


@pytest.mark.parametrize("adapter_name", ["manual", "provider_stub"])
def test_runner_adapter_contract_parity(adapter_name: str) -> None:
    adapters = registered_runner_adapters(enable_provider_stub=True)
    adapter: RunnerAdapter = adapters[adapter_name]
    run = {
        "run_id": f"run-{adapter_name}",
        "spec": {
            "manual_poll_state": "completed",
            "provider_poll_state": "completed",
        },
    }

    submitted = adapter.submit(run)
    assert isinstance(submitted, RunnerSubmitResult)
    assert submitted.job_id

    poll_running = adapter.poll(
        {
            **run,
            "spec": {
                **run["spec"],
                "manual_poll_state": "running",
                "provider_poll_state": "running",
            },
        }
    )
    assert isinstance(poll_running, RunnerPollResult)
    assert poll_running.state == "running"

    poll_completed = adapter.poll(run)
    assert isinstance(poll_completed, RunnerPollResult)
    assert poll_completed.state == "completed"

    artifacts = adapter.fetch_artifacts(run)
    assert isinstance(artifacts, list)
    assert artifacts

    cancelled = adapter.cancel(run)
    assert isinstance(cancelled, RunnerPollResult)
    assert cancelled.state == "cancelled"


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


def test_runner_execute_provider_adapter_reason_mapping() -> None:
    app = create_app()
    app.runner = app.runner.__class__(
        db=app.db,
        adapters=registered_runner_adapters(enable_provider_stub=True),
        default_adapter_name="manual",
    )
    app.propose_agent_run(
        spec=_minimal_spec(
            "run-provider-fail",
            adapter="provider_stub",
            provider_poll_state="failed",
            provider_failure_reason="rate_limit",
            max_retries=0,
        ),
        created_by="alice",
    )
    app.transition_agent_run(
        "run-provider-fail",
        to_status="approved",
        reason_code="human_approved",
    )

    claimed = app.claim_agent_runs(worker_id="w1", limit=1)
    assert claimed and claimed[0]["run_id"] == "run-provider-fail"
    result = app.execute_claimed_agent_run(run_id="run-provider-fail", worker_id="w1")
    assert result["status"] == "failed"

    persisted = app.db.get_agent_run("run-provider-fail")
    assert persisted is not None
    assert persisted["last_error"] == "provider_rate_limited"


def test_runner_context_guardrail_blocks_write_credentials() -> None:
    app = create_app()

    with pytest.raises(ValueError, match="runner_context_includes_write_credentials"):
        app.propose_agent_run(
            spec=_minimal_spec(
                "run-cred-blocked",
                context={"github_write_token": "ghp_1234567890abcdef"},
            ),
            created_by="alice",
        )


def test_runner_unknown_configured_default_falls_back_to_manual(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PM_BOT_RUNNER_DEFAULT_ADAPTER", "does-not-exist")
    app = create_app()
    run = app.propose_agent_run(
        spec={
            "run_id": "run-default-adapter",
            "model": "gpt-5",
            "intent": "default adapter",
            "requires_approval": True,
        },
        created_by="alice",
    )
    assert run["adapter_name"] == "manual"


def test_runner_rejects_unknown_adapter() -> None:
    app = create_app()
    with pytest.raises(ValueError, match="unknown_adapter"):
        app.propose_agent_run(
            spec=_minimal_spec("run-unknown-adapter", adapter="unknown-provider"),
            created_by="alice",
        )


def test_provider_adapter_not_enabled_by_default() -> None:
    app = create_app()
    with pytest.raises(ValueError, match="unknown_adapter"):
        app.propose_agent_run(
            spec=_minimal_spec("run-provider-disabled", adapter=ProviderStubRunnerAdapter.name),
            created_by="alice",
        )
