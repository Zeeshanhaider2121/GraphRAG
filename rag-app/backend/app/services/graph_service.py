"""Neo4j graph operations for documents, pages, sections, and retrieval."""
from __future__ import annotations

from collections import defaultdict
import json
import re
from typing import Any

from neo4j.exceptions import ClientError

from app.core.logging import setup_logging
from app.db.neo4j import get_neo4j_driver

logger = setup_logging(__name__)


class GraphService:
    """High-level graph CRUD + vector retrieval + full hierarchy builder."""

    PAGE_VECTOR_INDEX = "page_embedding_idx"
    SECTION_VECTOR_INDEX = "section_embedding_idx"

    def __init__(self) -> None:
        self.driver = get_neo4j_driver()

    # ── Schema ────────────────────────────────────────────────────────────

    def ensure_schema(self, embedding_dim: int) -> None:
        """Create basic constraints and indexes for ingestion/retrieval."""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chapter) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Page) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Section) REQUIRE s.id IS UNIQUE",
        ]
        page_index = f"""
            CREATE VECTOR INDEX {self.PAGE_VECTOR_INDEX} IF NOT EXISTS
            FOR (p:Page) ON (p.page_embedding)
            OPTIONS {{
                indexConfig: {{
                    `vector.dimensions`: {embedding_dim},
                    `vector.similarity_function`: 'cosine'
                }}
            }}
        """
        section_index = f"""
            CREATE VECTOR INDEX {self.SECTION_VECTOR_INDEX} IF NOT EXISTS
            FOR (s:Section) ON (s.section_embedding)
            OPTIONS {{
                indexConfig: {{
                    `vector.dimensions`: {embedding_dim},
                    `vector.similarity_function`: 'cosine'
                }}
            }}
        """
        full_text_indexes = [
            "CREATE FULLTEXT INDEX ft_page IF NOT EXISTS FOR (p:Page) ON EACH [p.header, p.markdown]",
            "CREATE FULLTEXT INDEX ft_section IF NOT EXISTS FOR (s:Section) ON EACH [s.title, s.number, s.content]",
        ]

        with self.driver.session() as session:
            for statement in constraints:
                session.run(statement)
            try:
                session.run(page_index)
                session.run(section_index)
            except ClientError as exc:
                logger.warning("Vector index creation warning: %s", exc)
            for statement in full_text_indexes:
                try:
                    session.run(statement)
                except ClientError as exc:
                    logger.warning("Full-text index creation warning: %s", exc)

    # ── ID helpers (from graph_creation.py) ───────────────────────────────

    @staticmethod
    def _band_id(num):
        return f"band_{num}"

    @staticmethod
    def _category_id(band_num, ctype):
        return f"cat_{band_num}_{ctype}"

    @staticmethod
    def _chapter_id(band_num, title, ctype):
        safe = title.replace(" ", "_").replace("/", "_")[:60]
        return f"ch_{band_num}_{ctype}_{safe}"

    @staticmethod
    def _section_id(page_idx, sec_idx, sec):
        num = (sec.get("number") or "").replace(" ", "_").replace("/", "_")
        title = (sec.get("title") or "")[:25].replace(" ", "_").replace("/", "_")
        return f"sec_p{page_idx}_i{sec_idx}_{num}_{title}"

    # ── Full hierarchy builder ─────────────────────────────────────────────

    def build_full_hierarchy(self, enriched_data: dict, document_id: str) -> None:
        """
        Create Book → Band → CategoryType → Chapter → Page → Section hierarchy,
        plus Tabelle, Bild, Formel nodes, directly in Neo4j.
        """
        pages = enriched_data["pages"]
        chapter_index = enriched_data["chapter_index"]
        metadata = enriched_data.get("metadata", {})

        # Extract book title and bands
        book_title = self._extract_book_title(metadata, pages)
        book_subtitle = self._extract_subtitle(pages)
        book_id_safe = "book_" + book_title.lower().replace(" ", "_")[:40]
        band_nums = {ch.get("band") for ch in chapter_index if ch.get("band") is not None}
        band_titles = self._extract_band_titles(pages, chapter_index)

        ctypes_per_band = defaultdict(set)
        for ch in chapter_index:
            bn = ch.get("band", 0)
            ctype = ch.get("chapter_type", "chapter")
            if ctype in ("front_matter", "chapter", "main_chapter", "appendix"):
                ctypes_per_band[bn].add(ctype)

        # Build chapter lookup for later linking
        chapter_lookup = {}
        for ch in chapter_index:
            bn = ch.get("band", 0)
            title = (ch.get("chapter") or "").strip()
            ctype = ch.get("chapter_type", "chapter")
            chapter_lookup[(bn, title, ctype)] = self._chapter_id(bn, title, ctype)

        with self.driver.session() as session:
            # 1. Schema constraints
            self._setup_full_schema(session)

            # 2. Book + Bands
            session.run(
                """
                MERGE (bk:Book {id: $id})
                SET bk.title = $title, bk.subtitle = $sub
                """, id=book_id_safe, title=book_title, sub=book_subtitle
            )
            for num in sorted(band_nums):
                session.run(
                    """
                    MERGE (bd:Band {id: $id})
                    SET bd.number = $num, bd.title = $title
                    WITH bd
                    MATCH (bk:Book {id: $book_id})
                    MERGE (bk)-[:HAS_BAND]->(bd)
                    """, id=self._band_id(num), num=num,
                    title=band_titles.get(num, f"Band {num}"),
                    book_id=book_id_safe
                )

            # 3. CategoryType nodes
            for num in sorted(band_nums):
                for ctype in ctypes_per_band.get(num, []):
                    cat_id = self._category_id(num, ctype)
                    label = {
                        "front_matter": "Front Matter",
                        "main_chapter": "Main Chapters",
                        "chapter": "Main Chapters",
                        "appendix": "Appendices",
                    }.get(ctype, ctype)
                    session.run(
                        """
                        MERGE (cat:CategoryType {id: $id})
                        SET cat.type = $ctype, cat.label = $label, cat.band = $band
                        WITH cat
                        MATCH (bd:Band {id: $band_id})
                        MERGE (bd)-[:HAS_CATEGORY]->(cat)
                        """, id=cat_id, ctype=ctype, label=label,
                        band=num, band_id=self._band_id(num)
                    )

            # 4. Chapter nodes
            for ch in chapter_index:
                bn = ch.get("band", 0)
                title = (ch.get("chapter") or "").strip()
                ctype = ch.get("chapter_type", "chapter")
                sp = ch.get("start_page")
                ep = ch.get("end_page")
                ch_id = self._chapter_id(bn, title, ctype)
                cat_id = self._category_id(bn, ctype)
                session.run(
                    """
                    MERGE (c:Chapter {id: $id})
                    SET c.title = $title, c.chapter_type = $ctype,
                        c.band = $band, c.start_page = $sp, c.end_page = $ep,
                        c.page_count = $pc
                    WITH c
                    MATCH (cat:CategoryType {id: $cat_id})
                    MERGE (cat)-[:CONTAINS_CHAPTER]->(c)
                    """, id=ch_id, title=title, ctype=ctype,
                    band=bn, sp=sp, ep=ep,
                    pc=(ep - sp + 1) if (sp is not None and ep is not None) else None,
                    cat_id=cat_id
                )

            # 5. Pages and sections (batched)
            self._load_pages_and_sections(session, pages, chapter_lookup)

    # ── Helper methods for full hierarchy ─────────────────────────────────

    def _extract_book_title(self, metadata, pages):
        title = (metadata.get("book_title") or "").strip()
        if title:
            return title
        for page in pages:
            header = page.get("header") or ""
            first_line = header.splitlines()[0].strip() if header else ""
            if first_line and not re.match(r'^Band\s+\d+', first_line, re.IGNORECASE):
                return first_line
        return "Unknown Book"

    def _extract_subtitle(self, pages):
        if pages:
            first_page_header = (pages[0].get("header") or "")
            lines = first_page_header.splitlines()
            if len(lines) > 1:
                return lines[1].strip()
        return ""

    def _extract_band_titles(self, pages, chapter_index):
        active_bands = {ch.get("band") for ch in chapter_index if ch.get("band") is not None}
        titles = {}
        for page in pages:
            bn = page.get("band")
            if bn not in active_bands or bn in titles:
                continue
            for line in (page.get("header") or "").splitlines():
                m = re.match(r'(Band\s+\d+\s*:.*)', line.strip(), re.IGNORECASE)
                if m:
                    titles[bn] = m.group(1).strip()
                    break
        for bn in active_bands:
            if bn not in titles:
                titles[bn] = f"Band {bn}"
        return titles

    def _setup_full_schema(self, session):
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Book) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Band) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:CategoryType) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Chapter) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Page) REQUIRE n.index IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Section) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Tabelle) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Bild) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Formel) REQUIRE n.id IS UNIQUE",
        ]
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (n:Page) ON (n.chapter)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Page) ON (n.band)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Page) ON (n.chapter_type)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Section) ON (n.level)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Section) ON (n.number)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Chapter) ON (n.chapter_type)",
        ]
        for stmt in constraints + indexes:
            try:
                session.run(stmt)
            except Exception as e:
                logger.warning("Schema statement warning: %s", e)

    def _load_pages_and_sections(self, session, pages, chapter_lookup):
        BATCH_SIZE = 50
        batch = []
        prev_idx = None
        total = 0

        for page in pages:
            batch.append({"page": page, "prev_idx": prev_idx})
            prev_idx = page.get("index")
            if len(batch) >= BATCH_SIZE:
                session.execute_write(self._load_pages_transaction, batch, chapter_lookup)
                total += len(batch)
                batch = []
        if batch:
            session.execute_write(self._load_pages_transaction, batch, chapter_lookup)

    def _load_pages_transaction(self, tx, batch, chapter_lookup):
        for item in batch:
            page = item["page"]
            prev_idx = item["prev_idx"]
            idx = page.get("index", 0)
            band_num = page.get("band", 0)
            chapter = (page.get("chapter") or "").strip()
            ctype = page.get("chapter_type") or "ignore"
            dims = page.get("dimensions") or {}

            # Page node
            tx.run("""
                MERGE (p:Page {index: $idx})
                SET p.name = $name, p.index = $idx, p.markdown = $markdown,
                    p.header = $header, p.footer = $footer,
                    p.band = $band, p.chapter = $chapter, p.chapter_type = $ctype,
                    p.dpi = $dpi, p.height = $height, p.width = $width,
                    p.hyperlinks = $hyperlinks,
                    p.has_images = $has_images, p.has_tables = $has_tables,
                    p.section_count = $sec_count
            """,
                name=f"Page {idx}", idx=idx,
                markdown=page.get("markdown") or "",
                header=page.get("header") or "",
                footer=page.get("footer") or "",
                band=band_num, chapter=chapter, ctype=ctype,
                dpi=dims.get("dpi"), height=dims.get("height"), width=dims.get("width"),
                hyperlinks=json.dumps(page.get("hyperlinks") or []),
                has_images=len(page.get("images") or []) > 0,
                has_tables=len(page.get("tables") or []) > 0,
                sec_count=len(page.get("sections") or []),
            )

            # Link to chapter
            if chapter and band_num is not None:
                ch_id = chapter_lookup.get((band_num, chapter, ctype))
                if not ch_id:
                    for k, v in chapter_lookup.items():
                        if k[0] == band_num and k[1] == chapter:
                            ch_id = v
                            break
                if ch_id:
                    tx.run("MATCH (c:Chapter {id:$ch_id}), (p:Page {index:$idx}) MERGE (c)-[:HAS_PAGE]->(p)",
                           ch_id=ch_id, idx=idx)

            # NEXT_PAGE chain
            if prev_idx is not None:
                tx.run("MATCH (prev:Page {index:$prev}), (cur:Page {index:$cur}) MERGE (prev)-[:NEXT_PAGE]->(cur)",
                       prev=prev_idx, cur=idx)

            # Tables on page
            table_lookup = {}
            for tbl in (page.get("tables") or []):
                tbl_id = f"tbl_{tbl['id']}_p{idx}"
                table_lookup[tbl["id"]] = tbl_id
                tx.run("MERGE (t:Tabelle {id:$id}) SET t.source_id=$src, t.content=$content, t.page=$page "
                       "WITH t MATCH (p:Page {index:$idx}) MERGE (p)-[:HAS_RAW_TABLE]->(t)",
                       id=tbl_id, src=tbl.get("id", ""), content=(tbl.get("content") or "")[:3000], page=idx, idx=idx)

            # Images on page
            image_lookup = {}
            for img in (page.get("images") or []):
                img_id = img.get("id", "")
                b_id = f"bild_{img_id}_p{idx}"
                image_lookup[img_id] = b_id
                ann_raw = img.get("image_annotation") or "{}"
                try:
                    ann = json.loads(ann_raw)
                except Exception:
                    ann = {}
                caption = img.get("caption") or ""
                b64 = (img.get("image_base64") or "")[:200_000]
                tx.run("""
                    MERGE (b:Bild {id:$id})
                    SET b.filename=$filename, b.source_id=$src, b.caption=$caption,
                        b.image_type=$itype, b.description=$desc,
                        b.top_left_x=$tlx, b.top_left_y=$tly,
                        b.bot_right_x=$brx, b.bot_right_y=$bry,
                        b.image_base64=$b64, b.page=$page
                    WITH b MATCH (p:Page {index:$idx}) MERGE (p)-[:HAS_IMAGE]->(b)
                """,
                    id=b_id, filename=img_id, src=img_id, caption=caption,
                    itype=ann.get("image_type", ""), desc=(ann.get("description") or "")[:500],
                    tlx=img.get("top_left_x"), tly=img.get("top_left_y"),
                    brx=img.get("bottom_right_x"), bry=img.get("bottom_right_y"),
                    b64=b64, page=idx, idx=idx)

            # Sections
            sections = page.get("sections") or []
            level_stack = {}
            for sec_idx, sec in enumerate(sections):
                level = sec.get("level", 0)
                sec_id = self._section_id(idx, sec_idx, sec)
                content = sec.get("content") or ""
                sec_formulas = sec.get("formulas") or []
                sec_images = sec.get("images") or []
                sec_tables = sec.get("tables") or []

                tx.run("""
                    MERGE (s:Section {id:$id})
                    SET s.level=$level, s.number=$number, s.title=$title,
                        s.raw_header=$hdr, s.content=$content,
                        s.content_preview=$preview, s.start_page=$sp,
                        s.end_page=$ep, s.has_formulas=$hf,
                        s.formula_count=$fmc, s.table_count=$tc,
                        s.figure_count=$fc
                    WITH s MATCH (p:Page {index:$idx})
                    MERGE (p)-[:HAS_SECTION {order:$order}]->(s)
                """,
                    id=sec_id, level=level, number=(sec.get("number") or ""),
                    title=(sec.get("title") or ""), hdr=(sec.get("raw_header") or ""),
                    content=content[:5000], preview=content[:300],
                    sp=sec.get("start_page"), ep=sec.get("end_page"),
                    hf=len(sec_formulas) > 0, fmc=len(sec_formulas),
                    tc=len(sec_tables), fc=len(sec_images),
                    idx=idx, order=sec_idx)

                if level > 1:
                    for pl in range(level - 1, 0, -1):
                        parent = level_stack.get(pl)
                        if parent:
                            tx.run("MATCH (ps:Section {id:$pid}), (cs:Section {id:$cid}) MERGE (ps)-[:HAS_SUBSECTION]->(cs)",
                                   pid=parent, cid=sec_id)
                            break
                level_stack[level] = sec_id
                for deeper in [l for l in list(level_stack.keys()) if l > level]:
                    del level_stack[deeper]

                if sec.get("end_page") and sec.get("start_page") and sec["end_page"] > sec["start_page"]:
                    tx.run("MATCH (s:Section {id:$sid}), (p:Page {index:$ep}) MERGE (s)-[:CONTINUES_ON]->(p)",
                           sid=sec_id, ep=sec["end_page"])

                # Formulas
                for f_i, formula in enumerate(sec_formulas):
                    if isinstance(formula, dict):
                        f_text = formula.get("plain_text") or formula.get("formula") or ""
                        f_katex = formula.get("katex_ready") or ""
                        f_tag = formula.get("tag") or ""
                        f_display = formula.get("display_mode", False)
                    else:
                        f_text, f_katex, f_tag, f_display = str(formula), "", "", False
                    f_id = f"formel_p{idx}_s{sec_idx}_f{f_i}"
                    tx.run("""
                        MERGE (f:Formel {id:$id})
                        SET f.text=$text, f.katex=$katex, f.tag=$tag,
                            f.display_mode=$display, f.page=$page, f.section_id=$sid
                        WITH f MATCH (s:Section {id:$sid}) MERGE (s)-[:HAS_FORMULA]->(f)
                    """, id=f_id, text=f_text[:500], katex=f_katex[:500],
                         tag=f_tag, display=f_display, page=idx, sid=sec_id)

                # Tables linked to section
                for t_i, tbl in enumerate(sec_tables):
                    raw_id = tbl.get("id", "") if isinstance(tbl, dict) else ""
                    t_id = table_lookup.get(raw_id) or f"tbl_{raw_id or t_i}_s{sec_idx}_p{idx}"
                    tx.run("""
                        MERGE (t:Tabelle {id:$id})
                        SET t.content=$content, t.page=$page
                        WITH t MATCH (s:Section {id:$sid}) MERGE (s)-[:HAS_TABLE]->(t)
                    """, id=t_id, content=(tbl.get("content") or "")[:3000] if isinstance(tbl, dict) else "",
                         page=idx, sid=sec_id)

                # Images linked to section
                for b_i, img in enumerate(sec_images):
                    if not isinstance(img, dict):
                        continue
                    raw_id = img.get("id", "")
                    b_id_v = image_lookup.get(raw_id) or f"bild_{raw_id or b_i}_s{sec_idx}_p{idx}"
                    ann_raw = img.get("image_annotation") or "{}"
                    try:
                        ann = json.loads(ann_raw)
                    except Exception:
                        ann = {}
                    caption = img.get("caption") or ""
                    b64 = (img.get("image_base64") or "")[:200_000]
                    tx.run("""
                        MERGE (b:Bild {id:$id})
                        SET b.filename=$filename, b.source_id=$src, b.caption=$caption,
                            b.image_type=$itype, b.description=$desc,
                            b.top_left_x=$tlx, b.top_left_y=$tly,
                            b.bot_right_x=$brx, b.bot_right_y=$bry,
                            b.image_base64=$b64, b.page=$page
                        WITH b MATCH (s:Section {id:$sid}) MERGE (s)-[:HAS_FIGURE]->(b)
                    """,
                        id=b_id_v, filename=raw_id, src=raw_id, caption=caption,
                        itype=ann.get("image_type", ""), desc=(ann.get("description") or "")[:500],
                        tlx=img.get("top_left_x"), tly=img.get("top_left_y"),
                        brx=img.get("bottom_right_x"), bry=img.get("bottom_right_y"),
                        b64=b64, page=idx, sid=sec_id)

    # ── Document tagging (for compatibility) ──────────────────────────────

    def tag_book_subgraph_with_document_id(self, *, book_id: str, document_id: str) -> None:
        """Attach document_id to nodes created by the full hierarchy."""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (b:Book {id: $book_id})
                SET b.document_id = $doc_id
                """, {"book_id": book_id, "doc_id": document_id}
            )
            session.run(
                """
                MATCH (b:Book {id: $book_id})-[:HAS_BAND]->(band:Band)
                SET band.document_id = $doc_id
                """, {"book_id": book_id, "doc_id": document_id}
            )
            session.run(
                """
                MATCH (b:Book {id: $book_id})-[:HAS_BAND]->(:Band)-[:HAS_CATEGORY]->(cat:CategoryType)
                SET cat.document_id = $doc_id
                """, {"book_id": book_id, "doc_id": document_id}
            )
            session.run(
                """
                MATCH (b:Book {id: $book_id})-[:HAS_BAND]->(:Band)-[:HAS_CATEGORY]->(:CategoryType)-[:CONTAINS_CHAPTER]->(ch:Chapter)
                SET ch.document_id = $doc_id
                """, {"book_id": book_id, "doc_id": document_id}
            )
            session.run(
                """
                MATCH (b:Book {id: $book_id})-[:HAS_BAND]->(:Band)-[:HAS_CATEGORY]->(:CategoryType)-[:CONTAINS_CHAPTER]->(:Chapter)-[:HAS_PAGE]->(p:Page)
                SET p.document_id = $doc_id
                """, {"book_id": book_id, "doc_id": document_id}
            )
            session.run(
                """
                MATCH (b:Book {id: $book_id})-[:HAS_BAND]->(:Band)-[:HAS_CATEGORY]->(:CategoryType)-[:CONTAINS_CHAPTER]->(:Chapter)-[:HAS_PAGE]->(:Page)-[:HAS_SECTION]->(s:Section)
                SET s.document_id = $doc_id
                """, {"book_id": book_id, "doc_id": document_id}
            )
            session.run(
                """
                MATCH (b:Book {id: $book_id})-[:HAS_BAND]->(:Band)-[:HAS_CATEGORY]->(:CategoryType)-[:CONTAINS_CHAPTER]->(:Chapter)-[:HAS_PAGE]->(:Page)-[:HAS_SECTION]->(:Section)-[:HAS_FORMULA]->(f:Formel)
                SET f.document_id = $doc_id
                """, {"book_id": book_id, "doc_id": document_id}
            )
            session.run(
                """
                MATCH (b:Book {id: $book_id})-[:HAS_BAND]->(:Band)-[:HAS_CATEGORY]->(:CategoryType)-[:CONTAINS_CHAPTER]->(:Chapter)-[:HAS_PAGE]->(:Page)-[:HAS_SECTION]->(:Section)-[:HAS_TABLE]->(t:Tabelle)
                SET t.document_id = $doc_id
                """, {"book_id": book_id, "doc_id": document_id}
            )
            session.run(
                """
                MATCH (b:Book {id: $book_id})-[:HAS_BAND]->(:Band)-[:HAS_CATEGORY]->(:CategoryType)-[:CONTAINS_CHAPTER]->(:Chapter)-[:HAS_PAGE]->(:Page)-[:HAS_SECTION]->(:Section)-[:HAS_FIGURE]->(bi:Bild)
                SET bi.document_id = $doc_id
                """, {"book_id": book_id, "doc_id": document_id}
            )

    # ── Original upsert (used by older pipeline) ─────────────────────────

    def upsert_document_graph(
        self,
        *,
        document_id: str,
        document_record: dict[str, Any],
        chapters: list[dict[str, Any]],
        pages: list[dict[str, Any]],
    ) -> None:
        """Upsert full document graph with pages and sections."""
        with self.driver.session() as session:
            session.run(
                """
                MERGE (d:Document {id: $id})
                SET d.filename = $filename,
                    d.original_filename = $original_filename,
                    d.file_hash = $file_hash,
                    d.file_size = $file_size,
                    d.content_type = $content_type,
                    d.source = $source,
                    d.status = $status,
                    d.page_count = $page_count,
                    d.created_at = coalesce(d.created_at, $created_at),
                    d.updated_at = $updated_at
                """,
                {
                    "id": document_id,
                    "filename": document_record.get("filename"),
                    "original_filename": document_record.get("original_filename"),
                    "file_hash": document_record.get("file_hash"),
                    "file_size": document_record.get("size"),
                    "content_type": document_record.get("content_type"),
                    "source": document_record.get("source", "upload"),
                    "status": document_record.get("status", "ready"),
                    "page_count": len(pages),
                    "created_at": document_record.get("created_at"),
                    "updated_at": document_record.get("updated_at"),
                },
            )

            session.run(
                """
                MATCH (d:Document {id: $doc_id})
                WITH d
                UNWIND $chapters AS chapter
                MERGE (c:Chapter {id: chapter.id})
                SET c.title = chapter.chapter,
                    c.chapter_type = chapter.chapter_type,
                    c.band = chapter.band,
                    c.start_page = chapter.start_page,
                    c.end_page = chapter.end_page,
                    c.document_id = $doc_id
                MERGE (d)-[:HAS_CHAPTER]->(c)
                """,
                {"doc_id": document_id, "chapters": chapters},
            )

            session.run(
                """
                MATCH (d:Document {id: $doc_id})
                WITH d
                UNWIND $pages AS page
                MERGE (p:Page {id: page.id})
                SET p.document_id = $doc_id,
                    p.page_index = page.index,
                    p.header = page.header,
                    p.footer = page.footer,
                    p.markdown = page.markdown,
                    p.chapter = page.chapter,
                    p.chapter_type = page.chapter_type,
                    p.chapter_id = page.chapter_id,
                    p.band = page.band,
                    p.dimensions_json = page.dimensions_json,
                    p.hyperlinks_json = page.hyperlinks_json,
                    p.page_embedding = page.page_embedding
                MERGE (d)-[:HAS_PAGE]->(p)
                WITH p, page
                UNWIND coalesce(page.sections, []) AS section
                MERGE (s:Section {id: section.id})
                SET s.document_id = $doc_id,
                    s.page_id = page.id,
                    s.level = section.level,
                    s.number = section.number,
                    s.title = section.title,
                    s.raw_header = section.raw_header,
                    s.content = section.content,
                    s.content_preview = section.content_preview,
                    s.start_page = section.start_page,
                    s.end_page = section.end_page,
                    s.section_embedding = section.section_embedding
                MERGE (p)-[:HAS_SECTION {order: section.order}]->(s)
                """,
                {"doc_id": document_id, "pages": pages},
            )

            session.run(
                """
                MATCH (d:Document {id: $doc_id})-[:HAS_PAGE]->(p:Page)
                MATCH (d)-[:HAS_CHAPTER]->(c:Chapter {id: p.chapter_id})
                MERGE (c)-[:HAS_PAGE]->(p)
                """,
                {"doc_id": document_id},
            )

            session.run(
                """
                MATCH (d:Document {id: $doc_id})-[:HAS_PAGE]->(p:Page)
                WITH p ORDER BY p.page_index ASC
                WITH collect(p) AS pages
                UNWIND range(0, size(pages) - 2) AS i
                WITH pages[i] AS current_page, pages[i + 1] AS next_page
                MERGE (current_page)-[:NEXT_PAGE]->(next_page)
                """,
                {"doc_id": document_id},
            )

    def search_similar_pages(self, embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        cypher = f"""
            CALL db.index.vector.queryNodes('{self.PAGE_VECTOR_INDEX}', $top_k, $embedding)
            YIELD node, score
            OPTIONAL MATCH (node)-[:HAS_SECTION]->(s:Section)
            WITH node, score, collect(s)[0..3] AS sections
            RETURN
                coalesce(node.id, toString(node.index)) AS id,
                node.document_id AS document_id,
                coalesce(node.page_index, node.index) AS page,
                node.header AS header,
                node.markdown AS markdown,
                score AS score,
                [section IN sections | {{
                    id: section.id,
                    title: section.title,
                    number: section.number,
                    content: section.content_preview
                }}] AS sections
            ORDER BY score DESC
        """
        with self.driver.session() as session:
            try:
                result = session.run(cypher, {"top_k": top_k, "embedding": embedding})
            except ClientError as exc:
                logger.warning("Vector search failed (index may be missing): %s", exc)
                return []
            return [record.data() for record in result]

    def delete_document_graph(self, document_id: str) -> None:
        with self.driver.session() as session:
            session.run(
                """
                MATCH (d:Document {id: $doc_id})
                OPTIONAL MATCH (d)-[:HAS_CHAPTER]->(c:Chapter)
                OPTIONAL MATCH (d)-[:HAS_PAGE]->(p:Page)
                OPTIONAL MATCH (p)-[:HAS_SECTION]->(s:Section)
                WITH [d] + collect(DISTINCT c) + collect(DISTINCT p) + collect(DISTINCT s) AS nodes
                UNWIND nodes AS node
                DETACH DELETE node
                """,
                {"doc_id": document_id},
            )
            session.run(
                """
                MATCH (n)
                WHERE n.document_id = $doc_id
                DETACH DELETE n
                """,
                {"doc_id": document_id},
            )