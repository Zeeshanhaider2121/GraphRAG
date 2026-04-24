import api from "./api";

export async function fetchDocuments() {
  const { data } = await api.get("/documents/list");
  return data;
}

export async function deleteDocument(docId) {
  const { data } = await api.delete(`/documents/${docId}`);
  return data;
}
