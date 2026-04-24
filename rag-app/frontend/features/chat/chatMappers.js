import { truncateText } from "../../utils/formatters";

function createId(prefix = "msg") {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function normalizeAssistantText(payload) {
  const rawText =
    payload?.result?.response ??
    payload?.result?.answer ??
    payload?.response ??
    payload?.answer ??
    payload?.result ??
    "I could not generate a response for this query.";

  if (typeof rawText === "string") return rawText;
  if (rawText && typeof rawText === "object") {
    return JSON.stringify(rawText, null, 2);
  }
  return "I could not generate a response for this query.";
}

function normalizeSources(payload) {
  const sourcePayload =
    payload?.result?.sources ?? payload?.sources ?? payload?.citations ?? payload?.references ?? [];

  const sourceList = Array.isArray(sourcePayload) ? sourcePayload : [sourcePayload];

  return sourceList
    .filter(Boolean)
    .map((source, index) => {
      if (typeof source === "string") {
        return {
          id: createId("src"),
          title: `Source ${index + 1}`,
          snippet: truncateText(source),
        };
      }

      return {
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
      };
    });
}

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
  };
}
