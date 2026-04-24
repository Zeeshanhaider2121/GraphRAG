import api from "./api";

export async function sendQuery({ query, topK = 5 }) {
  const payload = {
    query,
    top_k: topK,
  };
  const { data } = await api.post("/query/search", payload);
  return data;
}
