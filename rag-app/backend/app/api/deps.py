"""Dependency Injection"""
from typing import Generator
from app.db.neo4j import get_neo4j_session


def get_db_session() -> Generator:
    """Get Neo4j database session"""
    session = get_neo4j_session()
    try:
        yield session
    finally:
        session.close()
