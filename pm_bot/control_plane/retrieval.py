"""Retriever abstractions for local-first RAG integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class RetrievedChunk:
    """Retrieved text chunk with optional metadata."""

    chunk_id: str
    text: str
    score: float = 0.0
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ChunkUpsert:
    """Chunk payload used for upsert operations."""

    chunk_id: str
    text: str
    vector: list[float]
    metadata: dict[str, Any] | None = None


class Retriever(Protocol):
    """Protocol for vector retrieval backends."""

    def embed(self, text: str) -> list[float]:
        """Convert raw text into an embedding vector."""

    def upsert(self, chunks: list[ChunkUpsert]) -> None:
        """Upsert chunk vectors and metadata into the backend."""

    def query(
        self,
        vector: list[float],
        filters: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[RetrievedChunk]:
        """Query by vector similarity with optional backend filters."""


class StubRetriever:
    """No-op retriever implementation for local development and tests."""

    def embed(self, text: str) -> list[float]:
        if not text:
            return [0.0]
        # Deterministic stub: encode text length as a single-dimensional vector.
        return [float(len(text))]

    def upsert(self, chunks: list[ChunkUpsert]) -> None:
        _ = chunks

    def query(
        self,
        vector: list[float],
        filters: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[RetrievedChunk]:
        _ = (vector, filters, limit)
        return []
