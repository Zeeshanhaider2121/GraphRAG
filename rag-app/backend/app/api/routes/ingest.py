"""Document ingestion endpoints"""
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.ingest_service import IngestService
from app.services.storage_service import StorageService
from app.services.document_registry_service import DocumentRegistryService
from app.services.mistral_ocr_service import MistralOCRService
from app.services.enrichment_service import EnrichmentService
from app.services.graph_service import GraphService
from app.services.embedding_pipeline import EmbeddingPipeline
from app.services.embedding_service import EmbeddingService
from app.models.response_models import IngestResponse

# ── Create the full pipeline once (reused for all requests) ─────────────
_ingest_service = IngestService(
    storage_service=StorageService(),
    registry_service=DocumentRegistryService(),
    ocr_service=MistralOCRService(),
    enrichment_service=EnrichmentService(),
    graph_service=GraphService(),
    embedding_pipeline=EmbeddingPipeline(EmbeddingService()),
)

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/documents")
async def ingest_document(file: UploadFile = File(...)) -> IngestResponse:
    """Ingest a document into the RAG system"""
    try:
        result = await _ingest_service.ingest_document(file)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return IngestResponse(
        status="success",
        message=f"Document {file.filename} ingested successfully",
        document_id=result.get("document_id"),
        details=result,
    )