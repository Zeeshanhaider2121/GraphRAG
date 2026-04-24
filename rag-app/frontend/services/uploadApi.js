import api from "./api";

export async function uploadDocument(file, onUploadProgress) {
  const formData = new FormData();
  formData.append("file", file);

  const { data } = await api.post("/ingest/documents", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    timeout: 0,
    onUploadProgress,
  });

  return data;
}
