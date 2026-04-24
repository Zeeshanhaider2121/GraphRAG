"""Response models"""
from pydantic import BaseModel
from typing import Any, Optional, List


class QueryResponse(BaseModel):
    """Query response model"""
    query: str
    result: dict[str, Any]
    confidence: float = 0.0


class IngestResponse(BaseModel):
    """Ingest response model"""
    status: str
    message: str
    document_id: str | None = None
    details: dict[str, Any] | None = None


class DocumentListResponse(BaseModel):
    """Document list response model"""
    documents: list[dict[str, Any]]


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str
