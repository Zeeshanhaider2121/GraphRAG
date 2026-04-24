"""End-to-end document ingestion pipeline service (fully integrated)."""
from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.core.logging import setup_logging
from app.services.document_registry_service import DocumentRegistryService
from app.services.enrichment_service import EnrichmentService
from app.services.graph_service import GraphService
from app.services.embedding_pipeline import EmbeddingPipeline   # <-- changed
from app.services.embedding_service import EmbeddingService    
from app.services.mistral_ocr_service import MistralOCRService
from app.services.storage_service import StorageService

logger = setup_logging(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class IngestService:
    """
    Full ingestion pipeline:
    upload → Mistral OCR (chunked) → Enrichment (final_json logic)
        → Graph construction (Book/Band/Category/Chapter/Page/Section hierarchy)
        → Embeddings + vector/full-text indexes
    """

    def __init__(
        self,
        storage_service: StorageService | None = None,
        registry_service: DocumentRegistryService | None = None,
        ocr_service: MistralOCRService | None = None,
        enrichment_service: EnrichmentService | None = None,
        graph_service: GraphService | None = None,
        embedding_pipeline: EmbeddingPipeline | None = None,
    ) -> None:
        self.storage_service = storage_service or StorageService()
        self.registry_service = registry_service or DocumentRegistryService()
        self.ocr_service = ocr_service or MistralOCRService()
        self.enrichment_service = enrichment_service or EnrichmentService()
        self.graph_service = graph_service or GraphService()
        self.embedding_pipeline = embedding_pipeline or EmbeddingPipeline(EmbeddingService())

    @staticmethod
    def _build_document_id(file_bytes: bytes) -> str:
        checksum = hashlib.sha256(file_bytes).hexdigest()[:12]
        return f"doc_{checksum}_{uuid4().hex[:12]}"

    @staticmethod
    def _safe_log_excerpt(text: str | None, max_chars: int = 1800) -> str:
        if not text:
            return ""
        cleaned = text.strip()
        if len(cleaned) <= max_chars:
            return cleaned
        return f"{cleaned[:max_chars]}..."

    @staticmethod
    def _book_id_from_output(output_data: dict[str, Any]) -> str:
        metadata = output_data.get("metadata") if isinstance(output_data, dict) else {}
        if not isinstance(metadata, dict):
            metadata = {}
        title = str(metadata.get("book_title") or "").strip()
        if not title:
            pages = output_data.get("pages", []) if isinstance(output_data, dict) else []
            if pages:
                first_header = str(pages[0].get("header") or "").splitlines()
                title = first_header[0].strip() if first_header else ""
        if not title:
            title = "unknown_book"
        return "book_" + title.lower().replace(" ", "_")[:40]

    def _run_integrated_pipeline(
        self,
        *,
        document_id: str,
        combined_fixed_payload: dict[str, Any],
        filename: str,
    ) -> dict[str, Any]:
        """
        Execute enrichment, graph building, and embedding in-memory.
        Returns a dict with output_data, paths, book_id, and logs.
        """
        # 1. Enrich (final_json logic)
        logger.info("Running enrichment...")
        enriched = self.enrichment_service.enrich(combined_fixed_payload)

        # Save artifacts for backward compatibility
        enriched_artifact_path = self.storage_service.save_json_artifact(
            document_id, "enriched_document.json", enriched
        )
        output_artifact_path = self.storage_service.save_json_artifact(
            document_id, "output.json", enriched
        )

        # 2. Build full graph
        logger.info("Building graph hierarchy...")
        self.graph_service.build_full_hierarchy(enriched, document_id)

        # 3. Embed nodes and create indexes
        logger.info("Creating embeddings and indexes...")
        self.embedding_pipeline.create_indexes()
        self.embedding_pipeline.embed_all_nodes(document_id)

        book_id = self._book_id_from_output(enriched)
        # Tag the graph with document_id (if needed)
        self.graph_service.tag_book_subgraph_with_document_id(book_id=book_id, document_id=document_id)

        return {
            "paths": {
                "output_json": output_artifact_path,
                "enriched_document_json": enriched_artifact_path,
            },
            "book_id": book_id,
            "output_data": enriched,
            "logs": {},  # logs could be enhanced with per-step messages
        }

    def _ingest_sync(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
    ) -> dict[str, Any]:
        document_id = self._build_document_id(file_bytes)
        now = _utc_now()
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # Register initial document
        self.registry_service.upsert(
            {
                "id": document_id,
                "original_filename": filename,
                "filename": filename,
                "content_type": content_type,
                "size": len(file_bytes),
                "file_hash": file_hash,
                "source": "upload",
                "status": "received",
                "created_at": now,
                "updated_at": now,
            }
        )

        try:
            # Store original file
            storage_meta = self.storage_service.save_original_file(
                document_id,
                filename=filename,
                content=file_bytes,
                content_type=content_type,
            )
            self.registry_service.upsert(
                {
                    "id": document_id,
                    "filename": storage_meta["filename"],
                    "local_path": storage_meta["path"],
                    "status": "stored",
                }
            )

            # Run OCR
            ocr_result = self.ocr_service.extract_document(
                file_bytes=file_bytes,
                filename=storage_meta["filename"],
                content_type=content_type,
            )
            combined_payload = ocr_result.get("combined", {})
            combined_fixed_payload = ocr_result.get("combined_fixed", {})
            chunk_meta = ocr_result.get("chunks", [])

            # Save OCR intermediate files
            self.storage_service.save_json_artifact(
                document_id, "ocr_response_combined.json", combined_payload
            )
            combined_fixed_path = self.storage_service.save_json_artifact(
                document_id, "ocr_response_combined_fixed.json", combined_fixed_payload
            )
            self.registry_service.upsert(
                {
                    "id": document_id,
                    "status": "ocr_completed",
                    "ocr_raw_path": combined_fixed_path,
                    "page_count": len(combined_fixed_payload.get("pages", [])),
                }
            )

            # --- Integrated pipeline (enrich, graph, embed) ---
            pipeline_result = self._run_integrated_pipeline(
                document_id=document_id,
                combined_fixed_payload=combined_fixed_payload,
                filename=storage_meta["filename"],
            )

            output_data = pipeline_result["output_data"]
            page_count = len(output_data.get("pages", []))
            chapter_count = len(output_data.get("chapter_index", []))

            final_record = self.registry_service.upsert(
                {
                    "id": document_id,
                    "status": "ready",
                    "page_count": page_count,
                    "chapter_count": chapter_count,
                    "book_id": pipeline_result.get("book_id"),
                    "updated_at": _utc_now(),
                }
            )

            return {
                "document_id": document_id,
                "filename": storage_meta["filename"],
                "file_hash": file_hash,
                "page_count": page_count,
                "chapter_count": chapter_count,
                "status": final_record.get("status", "ready"),
                "ocr_chunk_size_pages": self.ocr_service.chunk_size_pages,
                "ocr_chunks": chunk_meta,
                "artifacts": pipeline_result.get("paths", {}),
                "logs": pipeline_result.get("logs", {}),
                "ocr_response_combined_fixed": {
                    "model": combined_fixed_payload.get("model"),
                    "usage_info": combined_fixed_payload.get("usage_info"),
                    "pages_count": len(combined_fixed_payload.get("pages", [])),
                    "first_page_index": (
                        combined_fixed_payload.get("pages", [{}])[0].get("index")
                        if combined_fixed_payload.get("pages")
                        else None
                    ),
                    "last_page_index": (
                        combined_fixed_payload.get("pages", [{}])[-1].get("index")
                        if combined_fixed_payload.get("pages")
                        else None
                    ),
                },
            }
        except Exception as exc:
            self.registry_service.upsert(
                {
                    "id": document_id,
                    "status": "failed",
                    "error": str(exc),
                    "updated_at": _utc_now(),
                }
            )
            logger.exception("Ingestion failed for %s: %s", document_id, exc)
            raise

    async def ingest_document(self, file: UploadFile) -> dict[str, Any]:
        """Handle upload end-to-end with blocking work offloaded to a thread."""
        file_bytes = await file.read()
        if not file_bytes:
            raise ValueError("Uploaded file is empty.")

        return await asyncio.to_thread(
            self._ingest_sync,
            file_bytes=file_bytes,
            filename=file.filename or "document.bin",
            content_type=file.content_type,
        )