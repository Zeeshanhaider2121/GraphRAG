"""HyDE + Two-Stage GraphRAG retrieval service with question expansion & reranking."""
from __future__ import annotations

import re
from typing import List, Tuple, Optional

from app.services.embedding_service import EmbeddingService
from app.services.graph_service import GraphService
from app.services.generation_service import GenerationService
from app.core.logging import setup_logging

logger = setup_logging(__name__)

# ── Real vector retrieval query (same as your working rag.py) ─────
VECTOR_RETRIEVAL_QUERY = """
OPTIONAL MATCH (ch:Chapter)-[:HAS_PAGE]->(node)
OPTIONAL MATCH (bd:Band)-[:HAS_CATEGORY]->(:CategoryType)-[:CONTAINS_CHAPTER]->(ch)
OPTIONAL MATCH (node)-[:HAS_SECTION]->(s:Section)
WITH node, score, ch, bd, s
WHERE s IS NOT NULL AND s.content IS NOT NULL AND trim(s.content) <> ''
OPTIONAL MATCH (s)-[:HAS_FORMULA]->(f:Formel)
WHERE f.text IS NOT NULL
WITH node, score, ch, bd, s,
     collect(DISTINCT {text: coalesce(f.text,''), tag: coalesce(f.tag,'')}) AS formulas
OPTIONAL MATCH (s)-[:HAS_TABLE]->(t:Tabelle)
WITH node, score, ch, bd, s, formulas,
     collect(DISTINCT coalesce(t.caption, t.source_id, '')) AS table_refs
OPTIONAL MATCH (s)-[:HAS_FIGURE]->(img:Bild)
WITH node, score, ch, bd, s, formulas, table_refs,
     collect(DISTINCT {caption: coalesce(img.caption,''), description: coalesce(img.description,'')}) AS figures
WITH score,
     '§' + coalesce(s.number,'?') + ' | ' + coalesce(s.title,'') + ' | ' +
     'p.' + toString(node.index) + ' | ' + 'Vol.' + toString(coalesce(bd.number,'?')) + ' | ' +
     coalesce(ch.title,'—') AS header,
     s.content AS body,
     [f IN formulas WHERE f.text <> '' | '  • ' + f.text + CASE WHEN f.tag <> '' THEN '  [' + f.tag + ']' ELSE '' END] AS formula_lines,
     [r IN table_refs WHERE r <> '' | '  • ' + r] AS table_lines,
     [img IN figures WHERE img.caption <> '' OR img.description <> '' |
         '  • ' + img.caption + CASE WHEN img.description <> '' THEN ' — ' + img.description ELSE '' END] AS figure_lines
WITH score,
     header + '\n' + body + '\n' +
     CASE WHEN size(formula_lines) > 0 THEN '\nFORMULAS:\n' + reduce(a='', x IN formula_lines | a + x + '\n') ELSE '' END +
     CASE WHEN size(table_lines) > 0 THEN '\nTABLES:\n' + reduce(a='', x IN table_lines | a + x + '\n') ELSE '' END +
     CASE WHEN size(figure_lines) > 0 THEN '\nFIGURES:\n' + reduce(a='', x IN figure_lines | a + x + '\n') ELSE '' END
     AS text
RETURN text, score
ORDER BY score DESC
"""

# ── Full‑text queries (same as before) ──────────────────────────
_FT_FORMULA = """
CALL db.index.fulltext.queryNodes('ft_formel', $query)
YIELD node AS f, score
MATCH (s:Section)-[:HAS_FORMULA]->(f)
MATCH (p:Page)-[:HAS_SECTION]->(s)
WHERE p.index IN $page_indexes
OPTIONAL MATCH (ch:Chapter)-[:HAS_PAGE]->(p)
OPTIONAL MATCH (bd:Band)-[:HAS_CATEGORY]->(:CategoryType)-[:CONTAINS_CHAPTER]->(ch)
RETURN 'formula' AS kind, coalesce(f.tag,'') AS tag, coalesce(f.text,'') AS text,
       coalesce(f.katex,'') AS extra, s.number AS section, coalesce(s.title,'') AS section_title,
       p.index AS page, coalesce(bd.number,'?') AS band, coalesce(ch.title,'—') AS chapter, score
ORDER BY score DESC LIMIT $limit
"""

_FT_TABLE = """
CALL db.index.fulltext.queryNodes('ft_tabelle', $query)
YIELD node AS t, score
MATCH (s:Section)-[:HAS_TABLE]->(t)
MATCH (p:Page)-[:HAS_SECTION]->(s)
WHERE p.index IN $page_indexes
OPTIONAL MATCH (ch:Chapter)-[:HAS_PAGE]->(p)
OPTIONAL MATCH (bd:Band)-[:HAS_CATEGORY]->(:CategoryType)-[:CONTAINS_CHAPTER]->(ch)
RETURN 'table' AS kind, coalesce(t.caption, t.source_id, '') AS tag,
       coalesce(t.content, t.caption, '') AS text, '' AS extra,
       s.number AS section, coalesce(s.title,'') AS section_title, p.index AS page,
       coalesce(bd.number,'?') AS band, coalesce(ch.title,'—') AS chapter, score
ORDER BY score DESC LIMIT $limit
"""

_FT_FIGURE = """
CALL db.index.fulltext.queryNodes('ft_bild', $query)
YIELD node AS img, score
MATCH (s:Section)-[:HAS_FIGURE]->(img)
MATCH (p:Page)-[:HAS_SECTION]->(s)
WHERE p.index IN $page_indexes
OPTIONAL MATCH (ch:Chapter)-[:HAS_PAGE]->(p)
OPTIONAL MATCH (bd:Band)-[:HAS_CATEGORY]->(:CategoryType)-[:CONTAINS_CHAPTER]->(ch)
RETURN 'figure' AS kind, coalesce(img.caption,'') AS tag,
       coalesce(img.description, img.caption, '') AS text, coalesce(img.image_type,'') AS extra,
       s.number AS section, coalesce(s.title,'') AS section_title, p.index AS page,
       coalesce(bd.number,'?') AS band, coalesce(ch.title,'—') AS chapter, score
ORDER BY score DESC LIMIT $limit
"""

_PAGE_IDX_RE = re.compile(r'\|\s*p\.(\d+)\s*\|')

_TAG_RES = [
    re.compile(r'(?:eq(?:uation)?\.?\s*|formula\s*|\()(\d+\.\d+[\w]*)\)?', re.I),
    re.compile(r'(?:tab(?:elle|le)?\.?\s*)([A-Za-z]?\s*\d+[\.\d]*)', re.I),
    re.compile(r'(?:fig(?:ure)?\.?\s*|bild\s*)(\d+[\.\d]*)', re.I),
]
_LUCENE_STRIP = re.compile(r'[+\-!(){}[\]^"~*?:\\/]')


class RetrievalService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        graph_service: GraphService,
        generation_service: GenerationService,
    ):
        self.embeddings = embedding_service
        self.graph = graph_service
        self.llm = generation_service
        self.top_k = 8
        self.artefact_limit = 6

    # ── Query Expansion ─────────────────────────────────────────────
    async def _expand_question(self, question: str, num_variants: int = 2) -> list[str]:
        """Generate semantically equivalent rephrasings of the question."""
        prompt = f"""You are a retrieval assistant. Given a technical question, generate {num_variants} alternative versions.
Each version must have the same meaning but be phrased differently.
Spell out abbreviations, ask for formulas directly, mention likely sections if known.
Output only the questions, one per line, without any other text.

Original: {question}

Alternatives:"""
        try:
            response = await self.llm.complete(prompt)
            lines = [line.strip() for line in response.splitlines() if line.strip()]
            unique = [question]
            for line in lines:
                if line not in unique:
                    unique.append(line)
                    if len(unique) >= num_variants + 1:
                        break
            return unique
        except Exception:
            return [question]

    # ── HyDE ────────────────────────────────────────────────────────
    async def _hyde(self, question: str) -> str:
        prompt = (
           "You are an Eurocode 7 geotechnical engineering expert.\n"
        "Write a short technical passage (4-6 sentences) exactly as it might appear "
        "in Eurocode 7 that would directly and completely answer the question below.\n"
        "Include relevant formula notation in plain text (e.g. Ed <= Rd).\n"
        "Output ONLY the passage, no preamble.\n\n"
        f"Question: {question}\n\n"
        "Write the passage in German:\n" 
        )
        return await self.llm.complete(prompt)

    # ── Vector search ───────────────────────────────────────────────
    async def _vector_search(self, embedding: list[float], top_k: int) -> tuple[list[str], list[int]]:
        with self.graph.driver.session() as session:
            result = session.run(
                """
                CALL db.index.vector.queryNodes('page_embedding_idx', $top_k, $embedding)
                YIELD node, score
                """ + VECTOR_RETRIEVAL_QUERY,
                top_k=top_k, embedding=embedding
            )
            section_blocks = []
            page_indexes = []
            seen_headers = set()
            for record in result:
                text = (record.get("text") or "").strip()
                if not text:
                    continue
                header = text.split('\n')[0]
                if header in seen_headers:
                    continue
                seen_headers.add(header)
                section_blocks.append(text)
                m = _PAGE_IDX_RE.search(header)
                if m:
                    pi = int(m.group(1))
                    if pi not in page_indexes:
                        page_indexes.append(pi)
            return section_blocks, page_indexes

    # ── Multi‑variant Stage 1 ───────────────────────────────────────
    async def stage1(self, question: str, top_k: int = 8) -> tuple[list[str], list[int]]:
        questions = await self._expand_question(question)
        all_blocks = []
        all_pages = []
        seen_headers = set()

        for q in questions:
            hyp = await self._hyde(q)
            vec = await self.embeddings.embed(hyp)
            blocks, pages = await self._vector_search(vec, top_k)
            for blk, pg in zip(blocks, pages):
                hdr = blk.split('\n')[0]
                if hdr not in seen_headers:
                    seen_headers.add(hdr)
                    all_blocks.append(blk)
                    if pg not in all_pages:
                        all_pages.append(pg)
            if len(all_blocks) >= top_k * 2:
                break
        return all_blocks, all_pages

    # ── Reranking ──────────────────────────────────────────────────
    async def _rerank(self, question: str, blocks: list[str], top_k: int = 5) -> list[str]:
        if not blocks:
            return blocks
        scored = []
        for block in blocks:
            text = block[:2000]
            rating_prompt = f"""On a scale of 0 to 10, how relevant is the following text to the question?
Answer with only the number.

Question: {question}

Text:
{text}

Relevance (0-10):"""
            try:
                response = await self.llm.complete(rating_prompt)
                score = int(response.strip())
                score = max(0, min(10, score))
            except Exception:
                score = 0
            scored.append((score, block))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [block for _, block in scored[:top_k]]

    # ── Stage 2 (unchanged from your existing code) ──────────────
    async def stage2(self, question: str, page_indexes: list[int]) -> list[str]:
        if not page_indexes:
            return []
        tags = self._extract_tags(question)
        ft_query = " OR ".join(tags) if tags else self._sanitise(question)
        if not ft_query.strip():
            return []
        rows = []
        with self.graph.driver.session() as session:
            for cypher in [_FT_FORMULA, _FT_TABLE, _FT_FIGURE]:
                try:
                    rows += session.run(
                        cypher,
                        query=ft_query,
                        page_indexes=page_indexes,
                        limit=self.artefact_limit,
                    ).data()
                except Exception as e:
                    logger.warning("Full‑text search failed (%s): %s", cypher[:20], e)
        rows.sort(key=lambda r: -r.get("score", 0))
        seen = set()
        blocks = []
        for row in rows:
            key = (row.get("kind"), row.get("tag"), row.get("page"))
            if key in seen:
                continue
            seen.add(key)
            block = self._fmt_artefact(row)
            if block:
                blocks.append(block)
            if len(blocks) >= self.artefact_limit:
                break
        return blocks

    # ── Helpers (unchanged) ──────────────────────────────────────
    @staticmethod
    def _extract_tags(question: str) -> list[str]:
        tags = []
        for pat in _TAG_RES:
            for m in pat.finditer(question):
                tag = m.group(1).strip().replace(" ", "")
                if tag and tag not in tags:
                    tags.append(tag)
        return tags

    @staticmethod
    def _sanitise(text: str) -> str:
        return re.sub(r'\s+', ' ', _LUCENE_STRIP.sub(' ', text)).strip()

    @staticmethod
    def _fmt_artefact(row: dict) -> str:
        kind = row.get("kind", "?")
        tag = row.get("tag", "")
        text = (row.get("text", "") or "").strip()
        section = row.get("section", "")
        sec_title = row.get("section_title", "")
        page = row.get("page", "?")
        chapter = row.get("chapter", "—")
        band = row.get("band", "?")
        if not text:
            return ""
        icon = {"formula": "📐", "table": "📊", "figure": "🖼️"}.get(kind, "•")
        lines = [f"{icon} {kind.upper()}  [{tag}]  |  p.{page}  |  Vol.{band}  |  {chapter}"]
        if section:
            lines.append(f"  §{section}  {sec_title}".rstrip())
        lines.append(text)
        return "\n".join(lines)

    # ── Combined retrieval ──────────────────────────────────────
    async def retrieve_context(self, question: str) -> tuple[list[str], list[str]]:
        sections, pages = await self.stage1(question, self.top_k)
        sections = await self._rerank(question, sections, top_k=5)
        artefacts = await self.stage2(question, pages)
        artefacts = await self._rerank(question, artefacts, top_k=3)
        return sections, artefacts