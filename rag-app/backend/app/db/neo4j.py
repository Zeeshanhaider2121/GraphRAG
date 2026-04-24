"""Neo4j database connection"""
from neo4j import GraphDatabase
from app.core.config import settings


_driver = None


def get_neo4j_driver():
    """Get Neo4j driver instance"""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
    return _driver


def get_neo4j_session():
    """Get Neo4j session"""
    driver = get_neo4j_driver()
    return driver.session()


def close_neo4j_driver():
    """Close Neo4j driver"""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
