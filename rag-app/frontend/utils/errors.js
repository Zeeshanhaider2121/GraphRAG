function readObjectErrorMessage(data) {
  if (!data || typeof data !== "object") return "";
  if (typeof data.message === "string" && data.message.trim()) return data.message;
  if (typeof data.detail === "string" && data.detail.trim()) return data.detail;
  if (Array.isArray(data.detail) && data.detail.length) {
    return data.detail.map((item) => item?.msg || item?.message || "").filter(Boolean).join(", ");
  }
  return "";
}

export function getApiErrorMessage(error, fallback = "Something went wrong. Please try again.") {
  if (!error) return fallback;

  const responseMessage = readObjectErrorMessage(error.response?.data);
  if (responseMessage) return responseMessage;

  if (typeof error.message === "string" && error.message.trim()) return error.message;
  return fallback;
}
