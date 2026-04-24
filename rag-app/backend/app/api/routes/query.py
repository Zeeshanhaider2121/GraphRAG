"""Query endpoints"""
from fastapi import APIRouter
from app.models.request_models import QueryRequest
from app.models.response_models import QueryResponse
from app.services.rag_pipeline import RAGPipeline

router = APIRouter(prefix="/query", tags=["query"])


@router.post("/search")
async def search_query(request: QueryRequest) -> QueryResponse:
    """Search for information using RAG pipeline"""
    pipeline = RAGPipeline()
    result = await pipeline.process_query(request.query, top_k=request.top_k)
    return QueryResponse(
        query=request.query,
        result=result,
        confidence=float(result.get("confidence", 0.0)),
    )
