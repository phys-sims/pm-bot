import asyncio
import json

from pm_bot.control_plane.api.app import ASGIServer, ServerApp
from pm_bot.control_plane.rag.ingestion import DocsIngestionService


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


def test_chunk_ids_are_stable_and_provenance_is_preserved(monkeypatch):
    monkeypatch.setenv("PMBOT_RAG_VECTOR_BACKEND", "memory")
    monkeypatch.setenv("PMBOT_RAG_EMBEDDING_PROVIDER", "local")
    service = DocsIngestionService(db=ServerApp().db, repo_root=".")

    first = service.index_docs(repo_id=0, chunk_lines=60)
    second = service.index_docs(repo_id=0, chunk_lines=60)

    assert first["revision_sha"] == second["revision_sha"]
    assert first["chunks_upserted"] == second["chunks_upserted"]

    hits = service.query("contract-first core objects", limit=3)
    assert hits
    metadata = hits[0].metadata
    assert metadata["source_path"].startswith("docs/")
    assert isinstance(metadata["line_start"], int)
    assert isinstance(metadata["line_end"], int)
    assert metadata["line_end"] >= metadata["line_start"]
    assert metadata["doc_type"] in {"spec", "contracts", "adr"}


def test_rag_http_routes_index_status_and_query(monkeypatch):
    monkeypatch.setenv("PMBOT_RAG_VECTOR_BACKEND", "memory")
    monkeypatch.setenv("PMBOT_RAG_EMBEDDING_PROVIDER", "local")

    app = ASGIServer(service=ServerApp())

    index_status, index_payload = _asgi_request(app, "POST", "/rag/index", body=b"{}")
    assert index_status == 200
    assert index_payload["status"] == "completed"
    assert index_payload["chunks_upserted"] > 0

    status_status, status_payload = _asgi_request(app, "GET", "/rag/status")
    assert status_status == 200
    assert status_payload["status"] == "completed"

    query_status, query_payload = _asgi_request(
        app,
        "GET",
        "/rag/query",
        query_string=b"q=github+integration&limit=2",
    )
    assert query_status == 200
    assert query_payload["summary"]["count"] >= 1
    row = query_payload["items"][0]
    assert "chunk_id" in row
    assert "metadata" in row
    assert row["metadata"]["source_path"].startswith("docs/")


def test_rag_query_requires_query_param(monkeypatch):
    monkeypatch.setenv("PMBOT_RAG_VECTOR_BACKEND", "memory")
    app = ASGIServer(service=ServerApp())

    status, payload = _asgi_request(app, "GET", "/rag/query")
    assert status == 400
    assert payload["error"] == "missing_q"
