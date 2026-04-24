"""Document management endpoints"""
from fastapi import APIRouter, HTTPException
from app.models.response_models import DocumentListResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/list")
async def list_documents() -> DocumentListResponse:
    """List all ingested documents"""
    service = DocumentService()
    return DocumentListResponse(documents=service.list_documents())


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document"""
    service = DocumentService()
    result = service.delete_document(doc_id)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=result["message"])
    return result
