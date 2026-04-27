import axios from "axios";

const configuredApiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";
const fallbackBaseUrl = import.meta.env.VITE_API_FALLBACK_BASE_URL || "http://localhost:8000";

function shouldRetryWithFallback(error) {
  const requestConfig = error?.config;
  if (!requestConfig || requestConfig.__fallbackRetried) return false;
  if (error?.response?.status !== 404) return false;
  return configuredApiBaseUrl.endsWith("/api/v1");
}

const api = axios.create({
  baseURL: configuredApiBaseUrl,
  timeout: 120000,
  headers: {
    Accept: "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("rag_access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (shouldRetryWithFallback(error)) {
      const nextConfig = {
        ...error.config,
        baseURL: fallbackBaseUrl,
        __fallbackRetried: true,
      };
      return api.request(nextConfig);
    }
    return Promise.reject(error);
  }
);

export default api;
export { configuredApiBaseUrl };
