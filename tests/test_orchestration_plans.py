import asyncio
import json

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
