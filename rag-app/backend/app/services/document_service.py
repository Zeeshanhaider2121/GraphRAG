"""Document management service for list and delete operations."""
from __future__ import annotations

from typing import Any

from app.services.document_registry_service import DocumentRegistryService
from app.services.graph_service import GraphService
from app.services.storage_service import StorageService


class DocumentService:
    """List and delete ingested documents."""

    def __init__(
        self,
        registry_service: DocumentRegistryService | None = None,
        graph_service: GraphService | None = None,
        storage_service: StorageService | None = None,
    ) -> None:
        self.registry_service = registry_service or DocumentRegistryService()
        self.graph_service = graph_service or GraphService()
        self.storage_service = storage_service or StorageService()

    def list_documents(self) -> list[dict[str, Any]]:
        """Return frontend-friendly list of uploaded documents."""
        rows = self.registry_service.list_active()
        output: list[dict[str, Any]] = []

        for row in rows:
            output.append(
                {
                    "id": row.get("id"),
                    "name": row.get("original_filename") or row.get("filename"),
                    "source": row.get("source", "upload"),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                    "size": row.get("size", 0),
                    "status": row.get("status", "unknown"),
                    "page_count": row.get("page_count", 0),
                }
            )

        return output

    def delete_document(self, document_id: str) -> dict[str, Any]:
        """Delete graph + local artifacts and mark registry entry deleted."""
        existing = self.registry_service.get(document_id)
        if existing is None:
            return {"status": "not_found", "message": f"Document {document_id} not found"}

        self.graph_service.delete_document_graph(document_id)
        self.storage_service.delete_document_data(document_id)
        self.registry_service.mark_deleted(document_id)
        return {"status": "success", "message": f"Document {document_id} deleted"}
