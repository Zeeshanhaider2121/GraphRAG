"""Query endpoint (HyDE + two‑stage GraphRAG)"""
from fastapi import APIRouter, Depends, HTTPException
from app.services.retrieval_service import RetrievalService
from app.services.embedding_service import EmbeddingService
from app.services.graph_service import GraphService
from app.services.generation_service import GenerationService

router = APIRouter(prefix="/query", tags=["query"])

# ── Inline dependency ──────────────────────────────────────────────────
def get_retrieval_service():
    return RetrievalService(
        embedding_service=EmbeddingService(),
        graph_service=GraphService(),
        generation_service=GenerationService(),
    )

@router.post("/")
async def ask_question(
    question: str,
    retrieval: RetrievalService = Depends(get_retrieval_service),
):
    """Ask a question against the ingested document(s)."""
    # 1. Retrieve context (sections + artefacts)
    sections, artefacts = await retrieval.retrieve_context(question)

    if not sections:
        return {
            "question": question,
            "answer": "No relevant content found in the document.",
            "sections": [],
            "artefacts": [],
        }

    # 2. Build answer with LLM
    prompt = build_answer_prompt(question, sections, artefacts)
    answer = await retrieval.llm.complete(prompt)

    # 3. Extract cited section (if any) and fetch source
    cited_section = parse_section_number(answer)
    source_box = ""
    if cited_section:
        sec = fetch_section_from_graph(retrieval.graph, cited_section)
        if sec:
            source_box = format_source_box(sec)

    return {
        "question": question,
        "answer": answer,
        "sections": sections,
        "artefacts": artefacts,
        "source_box": source_box,
    }

# ── Prompt builder (same as rag.py) ─────────────────────────────────────
def build_answer_prompt(question, sections, artefacts) -> str:
    sep = "\n\n" + "─" * 50 + "\n\n"
    sec_ctx = sep.join(sections) if sections else "(none)"
    art_ctx = sep.join(artefacts) if artefacts else "(none)"
    return f"""\
You are an Eurocode 7 expert (geotechnical engineering).
Answer the question ONLY using the retrieved content below.
**Answer in German**. Write formulas as plain text (no LaTeX). Be concise: 2-4 sentences.
Always state the exact formula if one appears in the context.
solute last line of your response must be:
SECTION: <number>    (example: SECTION: 2.4.7.1)
If the answer is not found: SECTION: —

════════════════════════════════════════════════════════════
SECTION CONTENT  (Stage 1 — vector search on Pages):

{sec_ctx}

════════════════════════════════════════════════════════════
ARTEFACTS  (Stage 2 — full-text on Formulas / Tables / Figures):

{art_ctx}

════════════════════════════════════════════════════════════
QUESTION: {question}

ANSWER FORMAT:
📖 Answer:
[2-4 sentences]

📐 Formula:
[plain text, e.g.  Ed <= Rd]
  Symbol | Meaning
  ------ | -------
  Ed     | ...

📌 Source:
  Section : <number> — <title>
  Page    : <number>
  Chapter : <name>
  Volume  : <number>

SECTION: <number>"""

# ── Section parsing (same as rag.py) ────────────────────────────────────
import re
_SECTION_RE = re.compile(
    r'SECTION\s*:\s*([A-Za-z]?\s*[\d][\d\.]*[\d]?[a-z]?|—)',
    re.IGNORECASE,
)

def parse_section_number(text: str):
    m = _SECTION_RE.search(text)
    if not m:
        return None
    val = m.group(1).strip()
    return None if val == "—" else val

def fetch_section_from_graph(graph_service, number: str):
    with graph_service.driver.session() as sess:
        rows = sess.run(
            """
            MATCH (s:Section {number: $num})
            OPTIONAL MATCH (p:Page)-[:HAS_SECTION]->(s)
            OPTIONAL MATCH (ch:Chapter)-[:HAS_PAGE]->(p)
            OPTIONAL MATCH (bd:Band)-[:HAS_CATEGORY]->(:CategoryType)-[:CONTAINS_CHAPTER]->(ch)
            OPTIONAL MATCH (s)-[:HAS_FORMULA]->(f:Formel)
              WHERE f.text IS NOT NULL
            OPTIONAL MATCH (s)-[:HAS_TABLE]->(t:Tabelle)
            OPTIONAL MATCH (s)-[:HAS_FIGURE]->(img:Bild)
            RETURN
                s.number  AS number,
                s.title   AS title,
                s.content AS content,
                p.index   AS page,
                ch.title  AS chapter,
                bd.number AS band,
                collect(DISTINCT {text: f.text, tag: f.tag}) AS formulas,
                collect(DISTINCT coalesce(t.caption, t.source_id)) AS tables,
                collect(DISTINCT {caption: img.caption, description: img.description}) AS figures
            LIMIT 1
            """,
            num=number,
        ).data()
        return rows[0] if rows else None

def format_source_box(sec: dict) -> str:
    lines = [
        "─" * 70,
        "  📂 SECTION SOURCE",
        "─" * 70,
        f"  §{sec.get('number','—')}  —  {sec.get('title','—')}",
        f"  Page {sec.get('page','—')}  |  Chapter: {sec.get('chapter','—')}  |  Volume {sec.get('band','—')}",
        "─" * 70,
    ]
    if sec.get("content"):
        lines.append("  Content:")
        for l in sec["content"].splitlines():
            lines.append(f"    {l}")
        lines.append("")
    formulas = [f for f in (sec.get("formulas") or []) if f and f.get("text")]
    if formulas:
        lines.append("  Formulas:")
        for f in formulas:
            suffix = f"  [{f['tag']}]" if f.get("tag") else ""
            lines.append(f"    • {f['text']}{suffix}")
    tables = [t for t in (sec.get("tables") or []) if t]
    if tables:
        lines.append("  Tables:")
        for t in tables:
            lines.append(f"    • {t}")
    figures = [fig for fig in (sec.get("figures") or []) if fig and (fig.get("caption") or fig.get("description"))]
    if figures:
        lines.append("  Figures:")
        for fig in figures:
            cap = fig.get("caption", "") or ""
            desc = fig.get("description", "") or ""
            lines.append(f"    • {cap}" + (f" — {desc}" if desc else ""))
    lines.append("─" * 70)
    return "\n".join(lines)