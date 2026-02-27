from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from pm_bot.control_plane.db.db import OrchestratorDB

DOC_GLOBS: tuple[str, ...] = ("docs/spec/*.md", "docs/contracts/*.md", "docs/adr/*.md")


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    source_path: str
    revision_sha: str
    line_start: int
    line_end: int
    doc_type: str
    text: str
    text_hash: str


@dataclass(frozen=True)
class QueryResult:
    chunk_id: str
    score: float
    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class QueryFilters:
    repo_id: int
    doc_types: tuple[str, ...] = ()


class LocalEmbeddingProvider:
    model = "local-hash"
    version = "v1"

    def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [round(b / 255.0, 6) for b in digest[:32]]


class OpenAIEmbeddingProvider:
    model = "text-embedding-3-small"
    version = "2024-01"

    def __init__(self, api_key: str, model: str | None = None) -> None:
        self.api_key = api_key
        if model:
            self.model = model

    def embed(self, text: str) -> list[float]:
        response = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "input": text},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return [float(v) for v in payload["data"][0]["embedding"]]


class QdrantIndex:
    def __init__(self, url: str, collection: str = "pm_bot_docs") -> None:
        self.url = url.rstrip("/")
        self.collection = collection
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        response = requests.get(f"{self.url}/collections/{self.collection}", timeout=10)
        if response.status_code == 200:
            return
        create = requests.put(
            f"{self.url}/collections/{self.collection}",
            json={"vectors": {"size": 32, "distance": "Cosine"}},
            timeout=10,
        )
        create.raise_for_status()

    def upsert(self, *, point_id: str, vector: list[float], payload: dict[str, Any]) -> None:
        response = requests.put(
            f"{self.url}/collections/{self.collection}/points",
            json={"points": [{"id": point_id, "vector": vector, "payload": payload}]},
            timeout=20,
        )
        response.raise_for_status()

    def query(self, *, vector: list[float], limit: int) -> list[dict[str, Any]]:
        response = requests.post(
            f"{self.url}/collections/{self.collection}/points/query",
            json={"query": vector, "with_payload": True, "limit": limit},
            timeout=20,
        )
        response.raise_for_status()
        return list(response.json().get("result", {}).get("points", []))


class InMemoryIndex:
    def __init__(self) -> None:
        self._points: dict[str, dict[str, Any]] = {}

    def upsert(self, *, point_id: str, vector: list[float], payload: dict[str, Any]) -> None:
        self._points[point_id] = {"id": point_id, "vector": vector, "payload": payload}

    def query(self, *, vector: list[float], limit: int) -> list[dict[str, Any]]:
        _ = vector
        rows = list(self._points.values())[:limit]
        return [{"id": row["id"], "score": 1.0, "payload": row["payload"]} for row in rows]


class DocsIngestionService:
    def __init__(self, db: OrchestratorDB, repo_root: Path | str = ".") -> None:
        self.db = db
        self.repo_root = Path(repo_root)
        self.embedding_provider = self._build_embedding_provider()
        self.embedding_model = f"{self.embedding_provider.model}:{self.embedding_provider.version}"
        self.index = self._build_index()

    def _build_embedding_provider(self) -> LocalEmbeddingProvider | OpenAIEmbeddingProvider:
        provider = os.environ.get("PMBOT_RAG_EMBEDDING_PROVIDER", "local").strip().lower()
        if provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY", "").strip()
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY is required when PMBOT_RAG_EMBEDDING_PROVIDER=openai"
                )
            model = os.environ.get("PMBOT_RAG_EMBEDDING_MODEL", "text-embedding-3-small").strip()
            return OpenAIEmbeddingProvider(api_key=api_key, model=model)
        return LocalEmbeddingProvider()

    def _build_index(self) -> QdrantIndex | InMemoryIndex:
        backend = os.environ.get("PMBOT_RAG_VECTOR_BACKEND", "qdrant").strip().lower()
        if backend == "memory":
            return InMemoryIndex()
        qdrant_url = os.environ.get("PMBOT_QDRANT_URL", "http://localhost:6333").strip()
        return QdrantIndex(
            url=qdrant_url,
            collection=os.environ.get("PMBOT_QDRANT_COLLECTION", "pm_bot_docs").strip()
            or "pm_bot_docs",
        )

    def index_docs(self, repo_id: int = 0, chunk_lines: int = 80) -> dict[str, Any]:
        revision_sha = self._revision_sha()
        job_id = str(uuid.uuid4())
        repo_fk = repo_id if repo_id > 0 else None
        scope = {"sources": list(DOC_GLOBS), "revision_sha": revision_sha}
        self.db.create_ingestion_job(job_id=job_id, repo_id=repo_fk, scope=scope)

        chunks_upserted = 0
        docs_indexed = 0
        for source_path in self._iter_sources():
            normalized_source_path = self._normalize_source_path(source_path)
            text = source_path.read_text(encoding="utf-8")
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            doc_id = self.db.upsert_document(
                source_type="governance_doc",
                source_path_or_url=normalized_source_path,
                repo_id=repo_fk,
                revision_sha=revision_sha,
                content_hash=content_hash,
            )
            docs_indexed += 1
            for chunk in self._chunk_source(
                source_path, normalized_source_path, revision_sha, chunk_lines
            ):
                vector = self.embedding_provider.embed(chunk.text)
                payload = {
                    "repo_id": repo_id,
                    "source_path": chunk.source_path,
                    "revision_sha": chunk.revision_sha,
                    "chunk_id": chunk.chunk_id,
                    "line_start": chunk.line_start,
                    "line_end": chunk.line_end,
                    "doc_type": chunk.doc_type,
                    "text": chunk.text,
                }
                self.index.upsert(point_id=chunk.chunk_id, vector=vector, payload=payload)
                self.db.upsert_chunk(
                    chunk_id=chunk.chunk_id,
                    doc_id=doc_id,
                    line_start=chunk.line_start,
                    line_end=chunk.line_end,
                    text_hash=chunk.text_hash,
                    token_count=max(1, len(chunk.text.split())),
                )
                self.db.upsert_embedding_record(
                    chunk_id=chunk.chunk_id,
                    qdrant_point_id=chunk.chunk_id,
                    embedding_model=self.embedding_model,
                )
                chunks_upserted += 1

        stats = {
            "documents_indexed": docs_indexed,
            "chunks_upserted": chunks_upserted,
            "embedding_model": self.embedding_model,
            "revision_sha": revision_sha,
            "status": "completed",
        }
        self.db.update_ingestion_job(job_id=job_id, status="completed", stats=stats)
        return {"job_id": job_id, **stats}

    def status(self) -> dict[str, Any]:
        return self.db.latest_ingestion_job() or {
            "status": "idle",
            "documents_indexed": 0,
            "chunks_upserted": 0,
        }

    def query(
        self,
        query_text: str,
        limit: int = 5,
        filters: QueryFilters | None = None,
    ) -> list[QueryResult]:
        resolved_filters = filters or QueryFilters(repo_id=0)
        vector = self.embedding_provider.embed(query_text)
        points = self.index.query(vector=vector, limit=max(limit * 4, limit))
        results: list[QueryResult] = []
        for point in points:
            payload = point.get("payload", {})
            point_repo_id = int(payload.get("repo_id", 0) or 0)
            if resolved_filters.repo_id and point_repo_id != resolved_filters.repo_id:
                continue
            point_doc_type = str(payload.get("doc_type", ""))
            if resolved_filters.doc_types and point_doc_type not in resolved_filters.doc_types:
                continue
            results.append(
                QueryResult(
                    chunk_id=str(payload.get("chunk_id", point.get("id", ""))),
                    score=float(point.get("score", 0.0)),
                    text=str(payload.get("text", "")),
                    metadata={
                        "repo_id": point_repo_id,
                        "source_path": payload.get("source_path"),
                        "revision_sha": payload.get("revision_sha"),
                        "line_start": payload.get("line_start"),
                        "line_end": payload.get("line_end"),
                        "doc_type": payload.get("doc_type"),
                    },
                )
            )
        return self._stable_order_results(results)[:limit]

    def _iter_sources(self) -> list[Path]:
        files: list[Path] = []
        for pattern in DOC_GLOBS:
            files.extend(sorted(self.repo_root.glob(pattern)))
        return [path for path in files if path.is_file()]

    def _chunk_source(
        self,
        source_path: Path,
        normalized_source_path: str,
        revision_sha: str,
        chunk_lines: int,
    ) -> list[ChunkRecord]:
        lines = source_path.read_text(encoding="utf-8").splitlines()
        doc_type = self._doc_type_for_source(normalized_source_path)
        chunks: list[ChunkRecord] = []
        for idx in range(0, len(lines), chunk_lines):
            start_line = idx + 1
            end_line = min(len(lines), idx + chunk_lines)
            text = "\n".join(lines[idx:end_line]).strip()
            if not text:
                continue
            raw_id = f"{normalized_source_path}:{revision_sha}:{start_line}:{end_line}".encode(
                "utf-8"
            )
            chunk_id = hashlib.sha256(raw_id).hexdigest()
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    source_path=normalized_source_path,
                    revision_sha=revision_sha,
                    line_start=start_line,
                    line_end=end_line,
                    doc_type=doc_type,
                    text=text,
                    text_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                )
            )
        return chunks

    def _normalize_source_path(self, source_path: Path) -> str:
        try:
            return source_path.resolve().relative_to(self.repo_root.resolve()).as_posix()
        except ValueError:
            return source_path.as_posix()

    def _revision_sha(self) -> str:
        head_path = self.repo_root / ".git" / "HEAD"
        if not head_path.exists():
            return "unknown"
        head = head_path.read_text(encoding="utf-8").strip()
        if head.startswith("ref:"):
            ref_path = self.repo_root / ".git" / head.split(" ", 1)[1]
            if ref_path.exists():
                return ref_path.read_text(encoding="utf-8").strip()
        return head

    def _doc_type_for_source(self, normalized_source_path: str) -> str:
        parts = normalized_source_path.split("/")
        if len(parts) >= 2 and parts[0] == "docs":
            return parts[1]
        return "unknown"

    def _stable_order_results(self, results: list[QueryResult]) -> list[QueryResult]:
        def _score_bucket(score: float) -> int:
            return int(score * 1000)

        return sorted(results, key=lambda row: (-_score_bucket(row.score), row.chunk_id))
