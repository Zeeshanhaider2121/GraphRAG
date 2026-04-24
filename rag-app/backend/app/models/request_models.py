"""Request models"""
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Query request model"""
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=50)


class LoginRequest(BaseModel):
    """Login request model"""
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)


class DocumentMetadata(BaseModel):
    """Document metadata"""
    source: str
    created_at: str
    updated_at: str
