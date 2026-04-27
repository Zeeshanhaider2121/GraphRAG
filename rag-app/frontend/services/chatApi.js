import api from "./api";

/**
 * Send a question to the RAG endpoint.
 * Backend route: POST /api/v1/query/?question=...
 * Returns: { question, answer, sections, artefacts, source_box }
 */
export async function sendQuery({ query, topK = 5 }) {
  const encoded = encodeURIComponent(query);
  const { data } = await api.post(`/query/?question=${encoded}&topK=${topK}`);
  return data;
}