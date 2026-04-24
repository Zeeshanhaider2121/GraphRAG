"""Response generation service for RAG answers."""
from __future__ import annotations

from typing import Any

from app.core.config import settings


class GenerationService:
    """Build answer text from retrieved sources."""

    def __init__(self) -> None:
        self.model_name = settings.LLM_MODEL
        self.api_key = settings.LLM_API_KEY

    async def generate(self, query: str, context_docs: list[dict[str, Any]]) -> str:
        """Generate a grounded answer."""
        if not context_docs:
            return (
                "I could not find matching evidence in the knowledge base yet. "
                "Upload documents or try a more specific question."
            )

        top_sources = context_docs[:3]
        bullets = []
        for index, source in enumerate(top_sources, start=1):
            page = source.get("page")
            title = source.get("title") or f"Source {index}"
            snippet = (source.get("snippet") or "").replace("\n", " ").strip()
            snippet = snippet[:220] + ("..." if len(snippet) > 220 else "")
            bullets.append(f"{index}. {title} (page {page}): {snippet}")

        return (
            f"Question: {query}\n\n"
            "Based on the most relevant indexed content, here are the key points:\n"
            + "\n".join(bullets)
        )
