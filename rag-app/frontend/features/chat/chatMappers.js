import { truncateText } from "../../utils/formatters";

function createId(prefix = "msg") {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

// ── Text extraction ──────────────────────────────────────────
function normalizeAssistantText(payload) {
  // Our RAG backend returns { answer, sections, artefacts, source_box }
  if (payload?.answer) return payload.answer;
  if (payload?.result?.response) return payload.result.response;
  if (payload?.response) return payload.response;
  if (payload?.result?.answer) return payload.result.answer;
  return "I could not generate a response for this query.";
}

// ── Source extraction ────────────────────────────────────────
function normalizeSources(payload) {
  const sources = [];

  // 1. Sections from RAG
  if (Array.isArray(payload?.sections)) {
    payload.sections.forEach((sec, idx) => {
      if (typeof sec !== "string") return;
      const header = sec.split("\n")[0] || `Section ${idx + 1}`;
      sources.push({
        id: createId("sec"),
        title: header,
        snippet: truncateText(sec, 500),
        type: "section",
      });
    });
  }

  // 2. Artefacts from RAG
  if (Array.isArray(payload?.artefacts)) {
    payload.artefacts.forEach((art, idx) => {
      if (typeof art !== "string") return;
      sources.push({
        id: createId("art"),
        title: art.split("\n")[0] || `Artefact ${idx + 1}`,
        snippet: truncateText(art, 500),
        type: "artefact",
      });
    });
  }

  // 3. Legacy source arrays (backwards compatibility)
  const legacySources =
    payload?.result?.sources ?? payload?.sources ?? payload?.citations ?? payload?.references ?? [];
  const sourceList = Array.isArray(legacySources) ? legacySources : [legacySources];
  sourceList.forEach((source, index) => {
    if (!source) return;   // skip null/undefined
    if (typeof source === "string") {
      sources.push({
        id: createId("src"),
        title: `Source ${index + 1}`,
        snippet: truncateText(source),
      });
      return;
    }
    sources.push({
      id: source.id || source.doc_id || source.document_id || createId("src"),
      title:
        source.title ||
        source.name ||
        source.file_name ||
        source.filename ||
        source.source ||
        `Source ${index + 1}`,
      snippet: truncateText(source.snippet || source.text || source.content || ""),
      score: Number.isFinite(Number(source.score)) ? Number(source.score) : null,
      page: source.page || source.page_number || source.chunk_index || null,
      url: source.url || source.link || null,
    });
  });

  // Remove any accidental undefined / null entries
  return sources.filter(Boolean);
}

// ── Public mappers ───────────────────────────────────────────
export function createUserMessage(text) {
  return {
    id: createId("usr"),
    role: "user",
    text,
    timestamp: new Date().toISOString(),
    sources: [],
  };
}

export function createAssistantErrorMessage(errorMessage) {
  return {
    id: createId("asst"),
    role: "assistant",
    text: errorMessage,
    timestamp: new Date().toISOString(),
    sources: [],
    sourceBox: "",
  };
}

export function mapQueryResponseToAssistantMessage(payload, fallbackQuery = "") {
  return {
    id: createId("asst"),
    role: "assistant",
    text: normalizeAssistantText(payload),
    timestamp: new Date().toISOString(),
    query: payload?.query || payload?.result?.query || fallbackQuery,
    confidence: Number(payload?.confidence ?? payload?.result?.confidence ?? 0),
    sources: normalizeSources(payload),
    sourceBox: payload?.source_box || payload?.sourceBox || "",
  };
}