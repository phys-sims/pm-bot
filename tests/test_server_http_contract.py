import asyncio
import json
import subprocess
import sys

from pm_bot.server.app import ASGIServer, ServerApp


def _asgi_request(app: ASGIServer, method: str, path: str, body: bytes = b"") -> tuple[int, dict]:
    scope = {"type": "http", "method": method, "path": path}
    sent: list[dict] = []
    received = False

    async def receive() -> dict:
        nonlocal received
        if received:
            return {"type": "http.request", "body": b"", "more_body": False}
        received = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict) -> None:
        sent.append(message)

    asyncio.run(app(scope, receive, send))

    status = next(msg["status"] for msg in sent if msg["type"] == "http.response.start")
    payload = b"".join(msg.get("body", b"") for msg in sent if msg["type"] == "http.response.body")
    return status, json.loads(payload.decode("utf-8"))


def test_documented_server_startup_command_is_available():
    result = subprocess.run(
        [sys.executable, "-m", "pm_bot.server.app", "--print-startup"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "uvicorn pm_bot.server.app:app --host 127.0.0.1 --port 8000" in result.stdout


def test_http_health_and_propose_changeset_flow():
    service = ServerApp()
    app = ASGIServer(service=service)

    health_status, health_payload = _asgi_request(app, "GET", "/health")
    assert health_status == 200
    assert health_payload == {"status": "ok"}

    propose_body = {
        "operation": "create_issue",
        "repo": "phys-sims/phys-pipeline",
        "payload": {"issue_ref": "#120", "title": "HTTP flow"},
    }
    status, payload = _asgi_request(
        app,
        "POST",
        "/changesets/propose",
        body=json.dumps(propose_body).encode("utf-8"),
    )
    assert status == 200
    assert payload["status"] == "pending"
    assert payload["operation"] == "create_issue"
