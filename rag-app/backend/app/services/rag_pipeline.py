"""Main RAG orchestration pipeline."""
from __future__ import annotations

from typing import Any

from fastapi import UploadFile

from app.services.embedding_service import EmbeddingService
from app.services.generation_service import GenerationService
from app.services.ingest_service import IngestService
from app.services.retrieval_service import RetrievalService


class RAGPipeline:
    """Orchestrates query and ingestion flows."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        retrieval_service: RetrievalService | None = None,
        generation_service: GenerationService | None = None,
        ingest_service: IngestService | None = None,
    ) -> None:
        self.embedding_service = embedding_service or EmbeddingService()
        self.retrieval_service = retrieval_service or RetrievalService()
        self.generation_service = generation_service or GenerationService()
        self.ingest_service = ingest_service or IngestService()

    async def process_query(self, query: str, top_k: int = 5) -> dict[str, Any]:
        """Process user query with embedding retrieval + response generation."""
        query_embedding = await self.embedding_service.embed(query)
        sources = await self.retrieval_service.retrieve(query_embedding, top_k=top_k)
        response = await self.generation_service.generate(query, sources)
        confidence = max((source.get("score") or 0.0 for source in sources), default=0.0)

        return {
            "query": query,
            "response": response,
            "sources": sources,
            "confidence": confidence,
        }

    async def ingest_document(self, file: UploadFile) -> dict[str, Any]:
        """Run full ingestion pipeline for uploaded document."""
        return await self.ingest_service.ingest_document(file)
