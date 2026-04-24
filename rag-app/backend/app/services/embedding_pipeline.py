
"""Embed graph nodes + create Neo4j vector & full-text indexes."""
from __future__ import annotations

import time
from typing import Any

from neo4j.exceptions import ClientError

from app.services.embedding_service import EmbeddingService
from app.db.neo4j import get_neo4j_driver
from app.core.logging import setup_logging

logger = setup_logging(__name__)


class EmbeddingPipeline:
    """Creates embeddings for all node types and sets up indexes."""

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self.embedding_service = embedding_service
        self.driver = get_neo4j_driver()

    # ── Text builders (same as embed_nodes.py) ──────────────────

    @staticmethod
    def _page_text(row: dict) -> str:
        parts = []
        if row.get("chapter"): parts.append(f"Kapitel: {row['chapter']}")
        if row.get("band"): parts.append(f"Band: {row['band']}")
        if row.get("header"): parts.append(str(row["header"]).strip())
        md = (row.get("markdown") or "").strip()
        if md: parts.append(md)
        return "\n".join(parts)

    @staticmethod
    def _section_text(row: dict) -> str:
        parts = []
        if row.get("chapter"): parts.append(f"Kapitel: {row['chapter']}")
        if row.get("number"): parts.append(f"Abschnitt {row['number']}")
        if row.get("raw_header"): parts.append(row["raw_header"])
        if row.get("title"): parts.append(row["title"])
        if row.get("content"): parts.append(row["content"])
        return "\n".join(parts)

    @staticmethod
    def _tabelle_text(row: dict) -> str:
        parts = []
        if row.get("section_number"): parts.append(f"Abschnitt {row['section_number']}")
        if row.get("section_title"): parts.append(row["section_title"])
        if row.get("page"): parts.append(f"Seite {row['page']}")
        if row.get("caption"): parts.append(row["caption"])
        if row.get("content"):
            clean = " ".join(
                l.replace("|", " ").strip()
                for l in (row["content"] or "").split("\n")
                if l.strip() and not l.strip().startswith("---")
            )
            parts.append(clean[:1500])
        return "\n".join(parts)

    @staticmethod
    def _bild_text(row: dict) -> str:
        parts = []
        if row.get("section_number"): parts.append(f"Abschnitt {row['section_number']}")
        if row.get("section_title"): parts.append(row["section_title"])
        if row.get("page"): parts.append(f"Seite {row['page']}")
        if row.get("caption"): parts.append(row["caption"])
        if row.get("image_type"): parts.append(f"Typ: {row['image_type']}")
        if row.get("description"): parts.append(row["description"][:1000])
        return "\n".join(parts)

    @staticmethod
    def _formel_text(row: dict) -> str:
        parts = []
        if row.get("tag"): parts.append(f"Formelbezeichnung: {row['tag']}")
        if row.get("section_number"): parts.append(f"Abschnitt {row['section_number']}")
        if row.get("section_title"): parts.append(row["section_title"])
        if row.get("page"): parts.append(f"Seite {row['page']}")
        if row.get("text"): parts.append(row["text"])
        if row.get("katex"): parts.append(f"LaTeX: {row['katex']}")
        return "\n".join(parts)

    # ── Index creation ────────────────────────────────────────

    def create_indexes(self) -> None:
        """Create vector and full-text indexes if they don't exist."""
        dims = self.embedding_service.vector_dimension

        vector_defs = [
            ("page_embedding_idx",    "Page",    "page_embedding"),
            ("section_embedding_idx", "Section", "section_embedding"),
            ("tabelle_embedding_idx", "Tabelle", "tabelle_embedding"),
            ("bild_embedding_idx",    "Bild",    "bild_embedding"),
            ("formel_embedding_idx",  "Formel",  "formel_embedding"),
        ]
        for name, label, prop in vector_defs:
            try:
                with self.driver.session() as session:
                    session.run(f"""
                        CREATE VECTOR INDEX {name} IF NOT EXISTS
                        FOR (n:{label}) ON (n.{prop})
                        OPTIONS {{
                            indexConfig: {{
                                `vector.dimensions`: {dims},
                                `vector.similarity_function`: 'cosine'
                            }}
                        }}
                    """)
                logger.info(f"Vector index created: {name}")
            except ClientError as e:
                if "already exists" not in str(e):
                    logger.warning(f"Vector index {name}: {e}")

        fulltext_defs = [
            ("ft_page",    "Page",    ["markdown", "header"]),
            ("ft_section", "Section", ["number", "raw_header", "title"]),
            ("ft_tabelle", "Tabelle", ["caption", "content"]),
            ("ft_bild",    "Bild",    ["caption", "description"]),
            ("ft_formel",  "Formel",  ["text", "katex", "tag"]),
        ]
        for name, label, props in fulltext_defs:
            try:
                with self.driver.session() as session:
                    exists = session.run(
                        "SHOW FULLTEXT INDEXES YIELD name WHERE name = $n RETURN count(*) > 0", n=name
                    ).single()[0]
                    if not exists:
                        props_str = "[n." + ", n.".join(props) + "]"
                        session.run(f"CREATE FULLTEXT INDEX {name} FOR (n:{label}) ON EACH {props_str}")
                        logger.info(f"Fulltext index created: {name}")
            except ClientError as e:
                if "already exists" not in str(e):
                    logger.warning(f"Fulltext index {name}: {e}")

    # ── Embedding routines (batched) ─────────────────────────

    def embed_all_nodes(self, document_id: str | None = None) -> None:
        """
        Embed all unembedded nodes of all types.
        Can be scoped to a specific document_id if needed.
        """
        # 1. Pages
        self._embed_pages()
        # 2. Sections
        self._embed_sections()
        # 3. Tabellen
        self._embed_node_type("Tabelle", "tabelle_embedding",
                              self._tabelle_text,
                              self._fetch_tabellen(),
                              self._write_tabelle)
        # 4. Bilder
        self._embed_node_type("Bild", "bild_embedding",
                              self._bild_text,
                              self._fetch_bilder(),
                              self._write_bild)
        # 5. Formeln
        self._embed_node_type("Formel", "formel_embedding",
                              self._formel_text,
                              self._fetch_formeln(),
                              self._write_formel)

    def _embed_pages(self) -> None:
        cypher = """
            MATCH (p:Page)
            WHERE p.markdown IS NOT NULL AND p.markdown <> '' AND p.page_embedding IS NULL
            OPTIONAL MATCH (ch:Chapter)-[:HAS_PAGE]->(p)
            OPTIONAL MATCH (bd:Band)-[:HAS_CATEGORY]->()-[:CONTAINS_CHAPTER]->(ch)
            RETURN p.index AS id, p.markdown AS markdown, p.header AS header,
                   ch.title AS chapter, bd.number AS band
        """
        with self.driver.session() as session:
            rows = session.run(cypher).data()
        if not rows:
            logger.info("All pages already embedded.")
            return
        self._batch_embed(rows, self._page_text, "Page", "page_embedding",
                          write_query="MATCH (p:Page {index: $id}) CALL db.create.setNodeVectorProperty(p, 'page_embedding', $embedding)")

    def _embed_sections(self) -> None:
        cypher = """
            MATCH (s:Section)
            WHERE s.content IS NOT NULL AND s.section_embedding IS NULL
            OPTIONAL MATCH (p:Page)-[:HAS_SECTION]->(s)
            OPTIONAL MATCH (ch:Chapter)-[:HAS_PAGE]->(p)
            RETURN s.id AS id, s.number AS number, s.raw_header AS raw_header,
                   s.title AS title, s.content AS content, ch.title AS chapter,
                   p.index AS page
        """
        with self.driver.session() as session:
            rows = session.run(cypher).data()
        if not rows:
            logger.info("All sections already embedded.")
            return
        self._batch_embed(rows, self._section_text, "Section", "section_embedding",
                          write_query="MATCH (s:Section {id: $id}) CALL db.create.setNodeVectorProperty(s, 'section_embedding', $embedding)")

    def _fetch_tabellen(self):
        with self.driver.session() as session:
            return session.run("""
                MATCH (t:Tabelle) WHERE t.tabelle_embedding IS NULL
                OPTIONAL MATCH (s:Section)-[:HAS_TABLE]->(t)
                RETURN t.id AS id, t.caption AS caption, t.content AS content,
                       t.page AS page, s.id AS section_id,
                       s.number AS section_number, s.title AS section_title
            """).data()

    def _write_tabelle(self, tx, row, vector):
        tx.run("""
            MATCH (t:Tabelle {id: $id})
            CALL db.create.setNodeVectorProperty(t, 'tabelle_embedding', $embedding)
            SET t.section_id = $section_id, t.section_number = $section_number
        """, **{**row, "embedding": vector})

    def _fetch_bilder(self):
        with self.driver.session() as session:
            return session.run("""
                MATCH (b:Bild) WHERE b.bild_embedding IS NULL
                OPTIONAL MATCH (s:Section)-[:HAS_FIGURE]->(b)
                RETURN b.id AS id, b.caption AS caption, b.description AS description,
                       b.image_type AS image_type, b.page AS page, b.source_id AS source_id,
                       s.id AS section_id, s.number AS section_number
            """).data()

    def _write_bild(self, tx, row, vector):
        tx.run("""
            MATCH (b:Bild {id: $id})
            CALL db.create.setNodeVectorProperty(b, 'bild_embedding', $embedding)
            SET b.section_id = $section_id, b.section_number = $section_number
        """, **{**row, "embedding": vector})

    def _fetch_formeln(self):
        with self.driver.session() as session:
            return session.run("""
                MATCH (f:Formel) WHERE f.formel_embedding IS NULL
                OPTIONAL MATCH (s:Section)-[:HAS_FORMULA]->(f)
                RETURN f.id AS id, f.text AS text, f.katex AS katex,
                       f.tag AS tag, s.number AS section_number,
                       s.title AS section_title, f.page AS page
            """).data()

    def _write_formel(self, tx, row, vector):
        tx.run("""
            MATCH (f:Formel {id: $id})
            CALL db.create.setNodeVectorProperty(f, 'formel_embedding', $embedding)
        """, **{**row, "embedding": vector})

    def _embed_node_type(self, label: str, prop_name: str,
                         text_builder, rows, write_func):
        if not rows:
            logger.info(f"No unembedded {label} nodes.")
            return
        self._batch_embed(rows, text_builder, label, prop_name,
                          write_func=write_func)

    def _batch_embed(self, rows, text_builder, label, prop_name, write_query=None, write_func=None):
        batch_size = self.embedding_service.batch_size
        total_written = 0
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            texts = [text_builder(r) for r in batch]
            vectors = self.embedding_service.embed_batch_sync(texts)
            with self.driver.session() as session:
                if write_func:
                    session.execute_write(self._write_batch_with_func, batch, vectors, write_func)
                else:
                    session.execute_write(self._write_batch, batch, vectors, write_query)
            total_written += len(batch)
            time.sleep(0.05)  # brief pause to avoid overwhelming Neo4j
            logger.info(f"Embedded {total_written}/{len(rows)} {label} nodes")
        logger.info(f"Finished embedding {label}: {total_written} written.")

    @staticmethod
    def _write_batch(tx, batch, vectors, write_query):
        for row, vec in zip(batch, vectors):
            if all(v == 0.0 for v in vec):
                continue
            params = dict(row)
            params["embedding"] = vec
            tx.run(write_query, **params)

    @staticmethod
    def _write_batch_with_func(tx, batch, vectors, write_func):
        for row, vec in zip(batch, vectors):
            if all(v == 0.0 for v in vec):
                continue
            write_func(tx, row, vec)
            