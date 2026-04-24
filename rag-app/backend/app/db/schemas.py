"""Database schemas"""
from typing import Any, Optional


class DocumentSchema:
    """Document schema"""
    
    id: str
    title: str
    content: str
    metadata: dict[str, Any]


class ChunkSchema:
    """Chunk schema"""
    
    id: str
    document_id: str
    content: str
    embedding: list[float]
    index: int
