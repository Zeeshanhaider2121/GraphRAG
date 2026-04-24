export function normalizeDocument(rawDocument, index = 0) {
  const metadata = rawDocument?.metadata ?? {};
  const name =
    rawDocument?.name ||
    rawDocument?.title ||
    rawDocument?.file_name ||
    rawDocument?.filename ||
    `Document ${index + 1}`;

  return {
    id: rawDocument?.id || rawDocument?.doc_id || rawDocument?.document_id || `${name}-${index}`,
    name,
    source: rawDocument?.source || metadata?.source || "Uploaded file",
    createdAt: rawDocument?.created_at || metadata?.created_at || null,
    updatedAt: rawDocument?.updated_at || metadata?.updated_at || null,
    size: Number(rawDocument?.size || metadata?.size || 0),
  };
}

export function mapDocumentListResponse(payload) {
  const documents = payload?.documents ?? [];
  if (!Array.isArray(documents)) return [];
  return documents.map(normalizeDocument);
}
