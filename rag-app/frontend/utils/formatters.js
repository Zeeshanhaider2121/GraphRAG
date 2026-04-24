export function formatMessageTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function formatDate(value) {
  if (!value) return "Unknown date";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatFileSize(bytes) {
  if (!bytes || Number.isNaN(Number(bytes))) return "Unknown size";
  const parsed = Number(bytes);
  if (parsed < 1024) return `${parsed} B`;
  if (parsed < 1024 * 1024) return `${(parsed / 1024).toFixed(1)} KB`;
  if (parsed < 1024 * 1024 * 1024) return `${(parsed / (1024 * 1024)).toFixed(1)} MB`;
  return `${(parsed / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

export function truncateText(text, maxLength = 180) {
  if (!text) return "";
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength).trim()}...`;
}
