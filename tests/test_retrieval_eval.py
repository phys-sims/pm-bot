import json
from pathlib import Path

from pm_bot.control_plane.rag.ingestion import DocsIngestionService, QueryFilters
from pm_bot.server.app import ServerApp


def test_retrieval_golden_snapshot_regression(tmp_path, monkeypatch):
    monkeypatch.setenv("PMBOT_RAG_VECTOR_BACKEND", "memory")
    monkeypatch.setenv("PMBOT_RAG_EMBEDDING_PROVIDER", "local")

    fixture = json.loads(Path("tests/fixtures/rag_golden_queries.json").read_text(encoding="utf-8"))
    for doc in fixture["corpus"]:
        file_path = tmp_path / doc["path"]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(doc["content"], encoding="utf-8")

    app = ServerApp()
    service = DocsIngestionService(db=app.db, repo_root=tmp_path)
    indexed = service.index_docs(repo_id=int(fixture["repo_id"]), chunk_lines=100)
    assert indexed["status"] == "completed"

    for query_case in fixture["queries"]:
        hits = service.query(
            query_text=query_case["query"],
            limit=int(query_case["top_k"]),
            filters=QueryFilters(
                repo_id=int(fixture["repo_id"]),
                doc_types=tuple(sorted(query_case.get("filters", {}).get("doc_types", []))),
            ),
        )
        assert [hit.chunk_id for hit in hits] == query_case["expected_chunk_ids"]
