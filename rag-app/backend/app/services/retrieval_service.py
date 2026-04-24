"""Hybrid retrieval service (vector currently, graph-ready for extension)."""
from __future__ import annotations

from typing import Any

from app.services.graph_service import GraphService


class RetrievalService:
    """Retrieve top-matching sources from graph storage."""

    def __init__(self, graph_service: GraphService | None = None) -> None:
        self.graph_service = graph_service or GraphService()

    async def retrieve(self, query_embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        """Fetch candidate source nodes from Neo4j vector index."""
        results = self.graph_service.search_similar_pages(query_embedding, top_k=top_k)
        sources: list[dict[str, Any]] = []

        for row in results:
            snippet = (row.get("markdown") or "").strip()
            if len(snippet) > 460:
                snippet = f"{snippet[:460].strip()}..."

            sources.append(
                {
                    "id": row.get("id"),
                    "document_id": row.get("document_id"),
                    "page": row.get("page"),
                    "title": row.get("header") or f"Page {row.get('page')}",
                    "score": float(row.get("score") or 0.0),
                    "snippet": snippet,
                    "sections": row.get("sections") or [],
                }
            )

        return sources
