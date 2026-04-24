"""Document ingestion endpoints"""
from fastapi import APIRouter, File, HTTPException, UploadFile
from app.services.rag_pipeline import RAGPipeline
from app.models.response_models import IngestResponse

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/documents")
async def ingest_document(file: UploadFile = File(...)) -> IngestResponse:
    """Ingest a document into the RAG system"""
    pipeline = RAGPipeline()
    try:
        result = await pipeline.ingest_document(file)
    except Exception as exc:  # pragma: no cover - depends on runtime systems
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return IngestResponse(
        status="success",
        message=f"Document {file.filename} ingested successfully",
        document_id=result.get("document_id"),
        details=result,
    )
