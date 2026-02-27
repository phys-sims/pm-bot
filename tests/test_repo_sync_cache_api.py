import asyncio
import json
from dataclasses import dataclass
from typing import Any

from pm_bot.server.app import ASGIServer, ServerApp
from pm_bot.server.github_auth import load_github_auth_from_env
from pm_bot.server.github_connector_api import GitHubAPIConnector


@dataclass
class FakeResponse:
    status_code: int
    payload: Any
    headers: dict[str, str] | None = None

    @property
    def content(self) -> bytes:
        if self.payload is None:
            return b""
        return b"json"

    def json(self) -> Any:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def request(self, **kwargs: Any) -> FakeResponse:
        self.calls.append(kwargs)
        if not self.responses:
            raise RuntimeError("No fake response left")
        return self.responses.pop(0)


def _asgi_request(
    app: ASGIServer,
    method: str,
    path: str,
    body: bytes = b"",
    query_string: bytes = b"",
) -> tuple[int, dict]:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": query_string,
    }
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


def test_repo_registry_sync_cache_end_to_end_with_incremental_cursor() -> None:
    session = FakeSession(
        [
            FakeResponse(
                200,
                [
                    {
                        "number": 11,
                        "state": "open",
                        "title": "Issue One",
                        "updated_at": "2026-02-27T00:00:00Z",
                    }
                ],
            ),
            FakeResponse(
                200,
                [
                    {
                        "number": 7,
                        "state": "open",
                        "title": "PR One",
                        "updated_at": "2026-02-27T00:10:00Z",
                    }
                ],
            ),
            FakeResponse(
                200,
                [
                    {
                        "number": 11,
                        "state": "closed",
                        "title": "Issue One closed",
                        "updated_at": "2026-02-27T00:20:00Z",
                    }
                ],
            ),
            FakeResponse(
                200,
                [
                    {
                        "number": 7,
                        "state": "closed",
                        "title": "PR One merged",
                        "updated_at": "2026-02-27T00:30:00Z",
                    }
                ],
            ),
        ]
    )
    connector = GitHubAPIConnector(
        allowed_repos={"phys-sims/phys-pipeline"},
        auth=load_github_auth_from_env({"PM_BOT_GITHUB_READ_TOKEN": "read-token"}),
        session=session,
    )
    service = ServerApp()
    service.connector = connector
    service.sync_service.connector = connector
    app = ASGIServer(service=service)

    add_status, add_payload = _asgi_request(
        app,
        "POST",
        "/repos/add",
        body=json.dumps({"full_name": "phys-sims/phys-pipeline", "since_days": 3}).encode("utf-8"),
    )
    assert add_status == 200
    repo_id = add_payload["id"]

    issues_status, issues_payload = _asgi_request(app, "GET", f"/repos/{repo_id}/issues")
    prs_status, prs_payload = _asgi_request(app, "GET", f"/repos/{repo_id}/prs")
    assert issues_status == 200
    assert prs_status == 200
    assert issues_payload["items"][0]["title"] == "Issue One"
    assert prs_payload["items"][0]["title"] == "PR One"

    sync_status, sync_payload = _asgi_request(app, "POST", f"/repos/{repo_id}/sync")
    assert sync_status == 200
    assert sync_payload["issues_upserted"] == 1
    assert sync_payload["prs_upserted"] == 1

    issues_status2, issues_payload2 = _asgi_request(app, "GET", f"/repos/{repo_id}/issues")
    prs_status2, prs_payload2 = _asgi_request(app, "GET", f"/repos/{repo_id}/prs")
    assert issues_status2 == 200
    assert prs_status2 == 200
    assert issues_payload2["items"][0]["state"] == "closed"
    assert prs_payload2["items"][0]["state"] == "closed"

    assert session.calls[0]["url"].endswith("/issues")
    assert session.calls[1]["url"].endswith("/pulls")
    assert "since" in session.calls[2]["params"]
    assert "since" in session.calls[3]["params"]


def test_repo_search_status_and_reindex_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("PMBOT_RAG_VECTOR_BACKEND", "memory")
    service = ServerApp()
    app = ASGIServer(service=service)

    add_status, add_payload = _asgi_request(
        app,
        "POST",
        "/repos/add",
        body=json.dumps({"full_name": "phys-sims/phys-pipeline"}).encode("utf-8"),
    )
    assert add_status == 200
    repo_id = int(add_payload["id"])

    search_status, search_payload = _asgi_request(
        app, "GET", "/repos/search", query_string=b"q=phys-sims"
    )
    assert search_status == 200
    assert any(item["full_name"] == "phys-sims/phys-pipeline" for item in search_payload["items"])

    status_code, status_payload = _asgi_request(app, "GET", f"/repos/{repo_id}/status")
    assert status_code == 200
    assert status_payload["repo_id"] == repo_id
    assert "issues_cached" in status_payload
    assert "prs_cached" in status_payload

    reindex_code, reindex_payload = _asgi_request(
        app,
        "POST",
        "/repos/reindex-docs",
        body=json.dumps({"repo_id": repo_id, "chunk_lines": 120}).encode("utf-8"),
    )
    assert reindex_code == 200
    assert reindex_payload["status"] == "completed"

    status_code2, status_payload2 = _asgi_request(app, "GET", f"/repos/{repo_id}/status")
    assert status_code2 == 200
    assert status_payload2["last_index_at"]

    missing_reindex_code, missing_reindex_payload = _asgi_request(
        app,
        "POST",
        "/repos/reindex-docs",
        body=json.dumps({"repo_id": repo_id + 999, "chunk_lines": 120}).encode("utf-8"),
    )
    assert missing_reindex_code == 404
    assert missing_reindex_payload["error"] == "repo_not_found"

    missing_shortcut_code, missing_shortcut_payload = _asgi_request(
        app,
        "POST",
        f"/repos/{repo_id + 999}/reindex",
    )
    assert missing_shortcut_code == 404
    assert missing_shortcut_payload["error"] == "repo_not_found"
