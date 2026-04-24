"""Neo4j service"""
from typing import Any
from app.db.neo4j import get_neo4j_session


class Neo4jService:
    """Service for Neo4j database operations"""
    
    def __init__(self):
        self.session = get_neo4j_session()
    
    def create_node(self, label: str, properties: dict[str, Any]) -> None:
        """Create a node in Neo4j"""
        query = f"CREATE (n:{label} {{{', '.join([f'{k}: ${k}' for k in properties.keys()])}}})"
        self.session.run(query, properties)
    
    def query(self, cypher_query: str, parameters: dict[str, Any] | None = None) -> list[Any]:
        """Execute a Cypher query"""
        result = self.session.run(cypher_query, parameters or {})
        return [record for record in result]
    
    def close(self) -> None:
        """Close the session"""
        self.session.close()
