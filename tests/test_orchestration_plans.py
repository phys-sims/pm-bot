import asyncio
import json
from pathlib import Path

from pm_bot.shared.settings import get_storage_settings

from pm_bot.server.app import ASGIServer, ServerApp


def _asgi_request(app: ASGIServer, method: str, path: str, body: dict | None = None):
    scope = {"type": "http", "method": method, "path": path, "query_string": b""}
    sent: list[dict] = []
    payload = json.dumps(body).encode("utf-8") if body is not None else b""
    delivered = False

    async def receive() -> dict:
        nonlocal delivered
        if delivered:
            return {"type": "http.request", "body": b"", "more_body": False}
        delivered = True
        return {"type": "http.request", "body": payload, "more_body": False}

    async def send(message: dict) -> None:
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    status = next(msg["status"] for msg in sent if msg["type"] == "http.response.start")
    body_bytes = b"".join(
        msg.get("body", b"") for msg in sent if msg["type"] == "http.response.body"
    )
    return status, json.loads(body_bytes.decode("utf-8"))


def test_plan_expansion_is_deterministic_snapshot() -> None:
    service = ServerApp()
    plan = {
        "tasks": [
            {"id": "build", "title": "Build", "inputs": {"cmd": "make build"}},
            {"id": "test", "title": "Test", "deps": ["build"], "inputs": {"cmd": "make test"}},
            {
                "id": "deploy",
                "title": "Deploy",
                "depends_on": ["test"],
                "inputs": {"cmd": "make deploy"},
            },
        ]
    }

    first = service.expand_plan(plan_id="plan-1", payload=plan, repo_id=1, source="test")
    second = service.expand_plan(plan_id="plan-1", payload=plan, repo_id=1, source="test")

    assert first["tasks"] == second["tasks"]
    assert first["edges"] == second["edges"]

    snapshot = {
        "tasks": [
            {
                "schema_version": "task_spec/v1",
                "task_id": "task_3a966aca22c65250",
                "title": "Build",
                "inputs": {"cmd": "make build"},
            },
            {
                "schema_version": "task_spec/v1",
                "task_id": "task_3c947c7f04e6701e",
                "title": "Test",
                "inputs": {"cmd": "make test"},
            },
            {
                "schema_version": "task_spec/v1",
                "task_id": "task_a01094aeb2ddff8d",
                "title": "Deploy",
                "inputs": {"cmd": "make deploy"},
            },
        ],
        "edges": [
            {"from_task": "task_3a966aca22c65250", "to_task": "task_3c947c7f04e6701e"},
            {"from_task": "task_3c947c7f04e6701e", "to_task": "task_a01094aeb2ddff8d"},
        ],
    }
    assert first["tasks"] == snapshot["tasks"]
    assert first["edges"] == snapshot["edges"]

    assert service.db.get_orchestration_plan("plan-1") is not None
    stored_task_runs = service.db.list_task_runs("plan-1")
    assert len(stored_task_runs) == 3
    assert stored_task_runs[1]["deps"] == ["task_3a966aca22c65250"]


def test_plan_expand_and_dag_http_routes() -> None:
    service = ServerApp()
    app = ASGIServer(service=service)

    expand_status, expand_payload = _asgi_request(
        app,
        "POST",
        "/plans/http-plan/expand",
        body={
            "repo_id": 1,
            "source": "http",
            "plan": {
                "tasks": [
                    {"id": "a", "title": "A"},
                    {"id": "b", "title": "B", "deps": ["a"]},
                ]
            },
        },
    )
    assert expand_status == 200
    assert expand_payload["plan_id"] == "http-plan"

    dag_status, dag_payload = _asgi_request(app, "GET", "/plans/http-plan/dag")
    assert dag_status == 200
    assert dag_payload["schema_version"] == "orchestration_dag/v1"
    assert len(dag_payload["tasks"]) == 2
    assert dag_payload["edges"]


def _write_changeset_artifact(run_id: str, bundle_payload: dict) -> str:
    settings = get_storage_settings()
    artifact_path = Path(settings.artifact_dir) / f"{run_id}.changeset_bundle.json"
    artifact_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "thread_id": f"thread-{run_id}",
                "graph_id": "repo_change_proposer/v1",
                "context_pack": {"schema_version": "context_pack/v2"},
                "changeset_bundle": bundle_payload,
            },
            sort_keys=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return artifact_path.resolve().as_uri()


def test_plan_aggregate_task_artifacts_merges_and_links_to_dag() -> None:
    service = ServerApp()
    plan = {
        "tasks": [
            {"id": "a", "title": "A"},
            {"id": "b", "title": "B"},
        ]
    }
    service.expand_plan(plan_id="agg-plan", payload=plan, repo_id=1, source="test")
    task_runs = service.db.list_task_runs("agg-plan")
    run_ids = ["run-agg-1", "run-agg-2"]
    payloads = [
        {
            "schema_version": "changeset_bundle_proposal/v1",
            "bundle": {
                "bundle_id": "bundle-1",
                "requires_human_approval": True,
                "changesets": [
                    {
                        "operation": "update_issue",
                        "repo": "acme/repo",
                        "target_ref": "#1",
                        "idempotency_key": "k-1",
                        "payload": {"body": "Body A"},
                    }
                ],
            },
        },
        {
            "schema_version": "changeset_bundle_proposal/v1",
            "bundle": {
                "bundle_id": "bundle-2",
                "requires_human_approval": True,
                "changesets": [
                    {
                        "operation": "update_issue",
                        "repo": "acme/repo",
                        "target_ref": "#2",
                        "idempotency_key": "k-2",
                        "payload": {"body": "Body B"},
                    }
                ],
            },
        },
    ]
    for idx, task_run in enumerate(task_runs):
        service.db.update_task_run_result(
            task_run["task_run_id"],
            status="succeeded",
            run_id=run_ids[idx],
            thread_id=f"thread-{idx}",
            clear_claim=True,
        )
        artifact_uri = _write_changeset_artifact(run_ids[idx], payloads[idx])
        service.db.set_agent_run_artifacts(run_ids[idx], [artifact_uri])

    app = ASGIServer(service=service)
    aggregate_status, aggregate_payload = _asgi_request(
        app,
        "POST",
        "/plans/agg-plan/aggregate",
        body={"requested_by": "reviewer"},
    )
    assert aggregate_status == 200
    assert aggregate_payload["status"] == "ready_for_review"
    assert aggregate_payload["candidate_count"] == 2

    dag_status, dag_payload = _asgi_request(app, "GET", "/plans/agg-plan/dag")
    assert dag_status == 200
    assert dag_payload["aggregation"]["artifact_uri"].endswith(".aggregated_changeset_bundle.json")


def test_plan_aggregate_conflicts_surface_as_interrupts() -> None:
    service = ServerApp()
    service.expand_plan(
        plan_id="conflict-plan",
        payload={"tasks": [{"id": "a", "title": "A"}, {"id": "b", "title": "B"}]},
        repo_id=1,
        source="test",
    )
    task_runs = service.db.list_task_runs("conflict-plan")
    for idx, task_run in enumerate(task_runs, start=1):
        run_id = f"run-conflict-{idx}"
        service.db.update_task_run_result(
            task_run["task_run_id"],
            status="succeeded",
            run_id=run_id,
            thread_id=f"thread-conflict-{idx}",
            clear_claim=True,
        )
        artifact_uri = _write_changeset_artifact(
            run_id,
            {
                "schema_version": "changeset_bundle_proposal/v1",
                "bundle": {
                    "bundle_id": f"bundle-conflict-{idx}",
                    "requires_human_approval": True,
                    "changesets": [
                        {
                            "operation": "update_issue",
                            "repo": "acme/repo",
                            "target_ref": "#9",
                            "idempotency_key": f"k-conflict-{idx}",
                            "payload": {"body": f"conflict-{idx}"},
                        }
                    ],
                },
            },
        )
        service.db.set_agent_run_artifacts(run_id, [artifact_uri])

    app = ASGIServer(service=service)
    aggregate_status, aggregate_payload = _asgi_request(
        app,
        "POST",
        "/plans/conflict-plan/aggregate",
        body={"requested_by": "reviewer"},
    )
    assert aggregate_status == 409
    assert aggregate_payload["error"] == "changeset_bundle_conflict_detected"

    interrupts = service.db.list_run_interrupts(run_id="plan:conflict-plan:aggregate")
    assert len(interrupts) == 1
    assert interrupts[0]["kind"] == "changeset_conflict"
    assert interrupts[0]["payload"]["reason_code"] == "changeset_bundle_conflict_detected"
